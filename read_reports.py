from gather import *
import configparser
import pandas as pd
from io import StringIO
import sys
from counters import *
from unit_hunt import common_function_pattern, add_to_tmp_stats
from source_code_analysis import Source_Code_Line, stalls_mapping_to_detail_report
from os import path
import numpy as np


def fill_report_ncu(report):
    with open(report.path, 'r') as fin:
        raw_content = fin.read()
    reg = re.compile(r'"ID","Process ID","Process Name"[\s\S]+')
    content = reg.findall(raw_content)
    if not content:
        reg2 = re.compile(r'ID,Time,API Call ID[\s\S]+')
        content = reg2.findall(raw_content)
        if not content:
            print("Report is empty or wrong format. Path: %s" % (report.path))
            exit(2)
    raw_counters_df = pd.read_csv(StringIO(content[0]), keep_default_na=False)
    return raw_counters_df


def select_all_counters_ncu(raw_counters_df, stats, kernel_id):
    raw_counters_df_first = raw_counters_df[kernel_id + 1:kernel_id + 2]
    missing = False
    for counter_name in counters_name_map_for_ncu:
        cname_in_ncu = counters_name_map_for_ncu[counter_name][0]
        if cname_in_ncu not in raw_counters_df_first.columns:
            missing = True
            print("The report doesn't has this counter: %s -> %s" % (counter_name, cname_in_ncu))
        else:
            as_type = counters_name_map_for_ncu[counter_name][1]
            tmp_stat = Stat(counter_name, cname_in_ncu)
            # if raw_counters_df_first.loc[kernel_id + 1, cname_in_ncu] != 'nan':

            raw_item = raw_counters_df_first.loc[kernel_id + 1, cname_in_ncu]
            tmp_stat.value = convert_raw_item(raw_item, as_type)
            stats[counter_name] = tmp_stat
            if counter_name == 'retireIPC':
                pass
    fill_missing_counters_ncu(raw_counters_df_first, stats, kernel_id)
    if missing:
        # @todo for debug, comment this temporarily.
        # exit(3)
        pass


def fill_missing_counters_ncu(raw_counters_df_first, stats, kernel_id):
    stats['gnic_lg_read_requests_postcoalescing'] = Stat('gnic_lg_read_requests_postcoalescing', 'missing', 1)
    stats['gnic_lg_read_requests_precoalescing'] = Stat('gnic_lg_read_requests_precoalescing', 'missing', 1)
    stats['global_ld_requests'] = Stat('global_ld_requests', 'missing', -1)
    stats['gnic_latency'] = Stat('gnic_latency', 'missing', -1)
    stats['mmu_ack_latency'] = Stat('mmu_ack_latency', 'missing', -1)
    stats['ltp_utlb_hit'] = Stat('ltp_utlb_hit', 'missing', 1)
    stats['ltp_utlb_miss'] = Stat('ltp_utlb_miss', 'missing', 1)
    l1_lines_per_instruction_avg_stat = Stat('l1_lines_per_instruction_avg', 'l1tex__t_set_accesses/l1tex__t_requests')
    l1_lines_per_instruction_avg_stat.value = stats['l1tex__t_set_accesses'].value / stats['l1tex__t_requests'].value
    stats['l1_lines_per_instruction_avg'] = l1_lines_per_instruction_avg_stat
    stats['gpcl1_tlb_hit'] = Stat('gpcl1_tlb_hit', 'missing', 1)
    stats['gpcl1_tlb_miss'] = Stat('gpcl1_tlb_miss', 'missing', 0)
    # @todo has already directly commented this counter in long_scoreboard_throughput()
    stats['ltp_utlb_arb_not_stalled'] = Stat('ltp_utlb_arb_not_stalled', 'missing', 0)
    # This counter is showed when l2 is bottleneck. Nothig else.
    stats['l2_bank_conflict'] = Stat('l2_bank_conflict', 'l2_bank_conflict', 0)
    # set it to 1 to avoid dividing by 0
    stats['l2_data_bank_accesses'] = Stat('l2_data_bank_accesses', 'l2_data_bank_accesses', 1)
    # dram__sectors / dram__activates
    stats['fb_accesses_per_activate'] = Stat('fb_accesses_per_activate', 'missing', -1)
    stats['dram_util'] = Stat('dram_util', 'missing', -1)
    stats['dram_throughput'] = Stat('dram_throughput', 'missing', -1)
    stats['average_latency_reads'] = Stat('average_latency_reads', 'missing', -1)
    stats['average_latency_writes'] = Stat('average_latency_writes', 'missing', -1)
    stats['average_dram_banks'] = Stat('average_dram_banks', 'missing', -1)
    stats['dram_lowBanks'] = Stat('dram_lowBanks', 'missing', -1)
    stats['dram_noReq'] = Stat('dram_noReq', 'missing', -1)
    stats['dram_turns'] = Stat('dram_turns', 'missing', -1)
    stats['imc_hitrate'] = Stat('imc_hitrate', 'missing', 1)

    stats['generic_ld_latency'] = Stat('generic_ld_latency', 'missing', 0)
    stats['shmem_ld_latency'] = Stat('shmem_ld_latency', 'missing', 0)
    stats['lg_ld_latency'] = Stat('lg_ld_latency', 'missing', 0)

    stats['inst_mem_geld_32b'] = Stat('inst_mem_geld_32b', 'missing', 0)
    stats['inst_mem_geld_64b'] = Stat('inst_mem_geld_64b', 'missing', 0)
    stats['inst_mem_geld_128b'] = Stat('inst_mem_geld_128b', 'missing', 0)
    stats['inst_mem_ldgsts_32b'] = Stat('inst_mem_ldgsts_32b', 'missing', 0)
    stats['inst_mem_ldgsts_64b'] = Stat('inst_mem_ldgsts_64b', 'missing', 0)
    stats['inst_mem_ldgsts_128b'] = Stat('inst_mem_ldgsts_128b', 'missing', 0)
    # @todo bug: inst related counters of rodinia/myocyte are nan. However, it do have memory operations.
    inst_mem_32b = convert_raw_item(
        raw_counters_df_first.loc[kernel_id + 1, 'sm__sass_inst_executed_op_memory_32b.sum']) + convert_raw_item(
        raw_counters_df_first.loc[kernel_id + 1, 'sm__sass_inst_executed_op_memory_8b.sum']) + convert_raw_item(
        raw_counters_df_first.loc[kernel_id + 1, 'sm__sass_inst_executed_op_memory_16b.sum'])
    inst_mem_64b = convert_raw_item(
        raw_counters_df_first.loc[kernel_id + 1, 'sm__sass_inst_executed_op_memory_64b.sum'])
    inst_mem_128b = convert_raw_item(
        raw_counters_df_first.loc[kernel_id + 1, 'sm__sass_inst_executed_op_memory_128b.sum'])
    inst_mem_Xb = inst_mem_32b + inst_mem_64b + inst_mem_128b
    inst_shared_ld = convert_raw_item(
        raw_counters_df_first.loc[kernel_id + 1, 'sm__sass_inst_executed_op_shared_ld.sum'])
    inst_global_ld = convert_raw_item(
        raw_counters_df_first.loc[kernel_id + 1, 'sm__sass_inst_executed_op_global_ld.sum'])
    inst_local_ld = convert_raw_item(raw_counters_df_first.loc[kernel_id + 1, 'sm__sass_inst_executed_op_local_ld.sum'])
    # This counter's value > inst_gld + inst_lld + inst_sld. Maybe missing somethig in report.
    # inst_mem_ld = int(raw_counters_df_first.loc[1, 'sm__sass_inst_executed_op_ld.sum'].replace(',', ''))
    inst_mem_ld = inst_global_ld + inst_shared_ld + inst_local_ld
    inst_shared_st = convert_raw_item(
        raw_counters_df_first.loc[kernel_id + 1, 'sm__sass_inst_executed_op_shared_st.sum'])
    inst_global_st = convert_raw_item(
        raw_counters_df_first.loc[kernel_id + 1, 'sm__sass_inst_executed_op_global_st.sum'])
    inst_local_st = convert_raw_item(raw_counters_df_first.loc[kernel_id + 1, 'sm__sass_inst_executed_op_local_st.sum'])
    inst_mem_st = inst_shared_st + inst_global_st + inst_local_st
    # the inst_mem_Xb is not same to the sum of global/local/shared op numbers which is strange
    stats['inst_mem_shared_ld_32b'] = Stat('inst_mem_shared_ld_32b', 'missing',
                                           inst_shared_ld * (inst_mem_32b / inst_mem_Xb))
    stats['inst_mem_shared_ld_64b'] = Stat('inst_mem_shared_ld_64b', 'missing',
                                           inst_shared_ld * (inst_mem_64b / inst_mem_Xb))
    stats['inst_mem_shared_ld_128b'] = Stat('inst_mem_shared_ld_128b', 'missing',
                                            inst_shared_ld * (inst_mem_128b / inst_mem_Xb))
    stats['shared_ld_requests'] = Stat('shared_ld_requests', 'sum(shared_ld_*b_executed)',
                                       stats['inst_mem_shared_ld_32b'].value + stats['inst_mem_shared_ld_64b'].value +
                                       stats['inst_mem_shared_ld_128b'].value)
    stats['inst_mem_shared_st_32b'] = Stat('inst_mem_shared_st_32b', 'missing',
                                           inst_shared_st * (inst_mem_32b / inst_mem_Xb))
    stats['inst_mem_shared_st_64b'] = Stat('inst_mem_shared_st_64b', 'missing',
                                           inst_shared_st * (inst_mem_64b / inst_mem_Xb))
    stats['inst_mem_shared_st_128b'] = Stat('inst_mem_shared_st_128b', 'missing',
                                            inst_shared_st * (inst_mem_128b / inst_mem_Xb))
    stats['shared_st_requests'] = Stat('shared_st_requests', 'sum(shared_st_*b_executed)',
                                       stats['inst_mem_shared_st_32b'].value + stats['inst_mem_shared_st_64b'].value +
                                       stats['inst_mem_shared_st_128b'].value)
    stats['inst_mem_gld_32b'] = Stat('inst_mem_gld_32b', 'missing',
                                     inst_global_ld * (inst_mem_32b / inst_mem_Xb))
    stats['inst_mem_gld_64b'] = Stat('inst_mem_gld_64b', 'missing',
                                     inst_global_ld * (inst_mem_64b / inst_mem_Xb))
    stats['inst_mem_gld_128b'] = Stat('inst_mem_gld_128b', 'missing',
                                      inst_global_ld * (inst_mem_128b / inst_mem_Xb))
    stats['generic_ld_32b_executed'] = Stat('generic_ld_32b_executed', 'missing',
                                            0 * (inst_mem_32b / inst_mem_Xb))
    stats['generic_ld_64b_executed'] = Stat('generic_ld_64b_executed', 'missing',
                                            0 * (inst_mem_32b / inst_mem_Xb))
    stats['generic_ld_128b_executed'] = Stat('generic_ld_128b_executed', 'missing',
                                             0 * (inst_mem_32b / inst_mem_Xb))
    stats['ldgsts_ld_32b_executed'] = Stat('ldgsts_ld_32b_executed', 'missing',
                                           0 * (inst_mem_32b / inst_mem_Xb))
    stats['ldgsts_ld_64b_executed'] = Stat('ldgsts_ld_64b_executed', 'missing',
                                           0 * (inst_mem_32b / inst_mem_Xb))
    stats['ldgsts_ld_128b_executed'] = Stat('ldgsts_ld_128b_executed', 'missing',
                                            0 * (inst_mem_32b / inst_mem_Xb))


def fill_stats(stats, report):
    """
    @arg stats: We store all stats(hw counters) in this argument.
    """
    raw_counters_df = fill_report_ncu(report)
    select_all_counters_ncu(raw_counters_df, stats, report.kernel_id)


def read_config(config_file_path, config):
    if not config_file_path.startswith('/'):
        config_file_path = "mem_config/" + config_file_path
    if not path.exists(config_file_path):
        print("Memory config file %s doesn't exist" % config_file_path)
        exit(1)
    else:
        print('Use "%s" as memory config' % (config_file_path))
    configparser_tmp = configparser.ConfigParser()
    configparser_tmp.read(config_file_path)
    configparser_tmp = configparser_tmp['Default']
    config.warp_size = int(configparser_tmp['warp_size'])
    config.quadrants_per_SM = int(configparser_tmp['quadrants_per_SM'])
    config.max_number_of_showed_nodes = int(configparser_tmp['max_number_of_showed_nodes'])
    config.max_percentage_of_showed_nodes = float(configparser_tmp['max_percentage_of_showed_nodes'])
    config.L1_THROUGHPUT_FIX = float(configparser_tmp['L1_THROUGHPUT_FIX'])
    config.uTLB_THROUGHPUT_FIX = float(configparser_tmp["uTLB_THROUGHPUT_FIX"])
    config.L1_TLB_THROUGHPUT_FIX = float(configparser_tmp['L1_TLB_THROUGHPUT_FIX'])
    config.BYTES_PER_L2_INSTRUCTION = int(configparser_tmp["BYTES_PER_L2_INSTRUCTION"])
    config.BYTES_PER_L1_INSTRUCTION = int(configparser_tmp['BYTES_PER_L1_INSTRUCTION'])
    config.L2_THROUGHPUT_FIX = float(configparser_tmp['L2_THROUGHPUT_FIX'])
    config.FB_THROUGHPUT_FIX = float(configparser_tmp['FB_THROUGHPUT_FIX'])
    config.conflict_high_threshold = float(configparser_tmp['conflict_high_threshold'])
    config.low_activewarps_per_activecycle = int(configparser_tmp['low_activewarps_per_activecycle'])
    config.L1_THROUGHPUT_PEAK = int(configparser_tmp['L1_THROUGHPUT_PEAK'])
    config.high_l1_throughput = float(configparser_tmp['high_l1_throughput'])
    config.high_l1_hit_rate = float(configparser_tmp['high_l1_hit_rate'])
    config.high_l1_conflict_rate = float(configparser_tmp['high_l1_conflict_rate'])
    config.low_access_per_activate = float(configparser_tmp['low_access_per_activate'])
    config.low_bank_per_access = float(configparser_tmp['low_bank_per_access'])
    config.within_load_coalescing_ratio = float(configparser_tmp['within_load_coalescing_ratio'])
    config.low_l1_hit_rate = float(configparser_tmp['low_l1_hit_rate'])
    config.high_utlb_miss_rate = float(configparser_tmp['high_utlb_miss_rate'])
    config.high_l2_miss_rate = float(configparser_tmp['high_l2_miss_rate'])
    config.high_l2_bank_conflict_rate = float(configparser_tmp['high_l2_bank_conflict_rate'])
    config.high_not_predicated_off_thread_per_inst_executed = int(
        configparser_tmp['high_not_predicated_off_thread_per_inst_executed'])
    config.max_not_predicated_off_thread_per_inst_executed = int(
        configparser_tmp['max_not_predicated_off_thread_per_inst_executed'])
    config.low_compress_rate = float(configparser_tmp['low_compress_rate'])
    config.L1_LATENCY_FIX = int(configparser_tmp['L1_LATENCY_FIX'])
    config.uTLB_LATENCY_FIX = int(configparser_tmp['uTLB_LATENCY_FIX'])
    config.l1TLB_LATENCY_FIX = int(configparser_tmp['l1TLB_LATENCY_FIX'])
    config.l2_latency = int(configparser_tmp['l2_latency'])
    config.fb_latency = int(configparser_tmp['fb_latency'])
    config.max_percentage_of_showed_source_code_nodes = float(
        configparser_tmp['max_percentage_of_showed_source_code_nodes'])
    config.max_number_of_showed_source_code_nodes = int(configparser_tmp['max_number_of_showed_source_code_nodes'])
    config.max_avtive_warps_per_SM = int(configparser_tmp['max_avtive_warps_per_SM'])
    config.compute_capability = int(configparser_tmp['compute_capability'])


def fill_source_report(report: Report, analysis: Analysis):
    source_df = pd.read_csv(report.source_report_path)
    for i in range(len(source_df)):
        analysis.source_lines.append(None)
    current_filename = source_df.iat[0, 1]
    for i in range(1, len(source_df)):
        code_line = Source_Code_Line()
        line_id = source_df.index.values[i]
        # code_line.line_number = line_number
        raw_line_content = source_df.at[line_id, 'Source']
        if type(raw_line_content) == str:
            raw_line_content = raw_line_content.strip()
        code_line.raw_line = raw_line_content
        x = source_df.at[line_id, '#']
        if np.isnan(x):
            current_filename = raw_line_content
            continue
        else:
            line_number = int(x)
        code_line.line_number = line_number
        code_line.file_name = current_filename
        analysis.source_lines[line_id] = code_line
        for stall_reason in stalls_mapping_to_detail_report:
            new_dict = {line_id: source_df.at[line_id, stall_reason]}
            cur_stall_reason = analysis.stall_sass_code.get(stalls_mapping_to_detail_report[stall_reason])
            if cur_stall_reason:
                cur_stall_reason.update(new_dict)
            else:
                analysis.stall_sass_code[stalls_mapping_to_detail_report[stall_reason]] = new_dict


def convert_raw_item(aitem, as_type=float):
    if aitem == 'nan':
        return 0
    real_type = type(aitem)

    if real_type in [float, int]:
        return aitem
    elif real_type == str:
        if as_type == str:
            return aitem
        else:
            if aitem.find('.') >= 0:
                return float(aitem.replace(',', ''))
            else:
                return int(aitem.replace(',', ''))
    else:
        print("unrecognized type of %s " % str(aitem))
        exit(-1)

def get_kernel_name(raw_kernel_name):
    if len(raw_kernel_name) > 20:
        left = raw_kernel_name.find("(")
        if left >= 0:
            return raw_kernel_name[:left]
        return raw_kernel_name[:20]
    else:
        return raw_kernel_name
