from data_struct import *
import re
import copy
import numpy as np


def add_to_tmp_stats(stats, final_stat_name, current_stat, suffix='', prefix=''):
    astat: Stat = stats.get(final_stat_name, None)
    if astat:
        astat.merge(current_stat)
    else:
        stats[final_stat_name] = copy.deepcopy(current_stat)
        stats[final_stat_name].name = final_stat_name
        stats[final_stat_name].suffix = suffix
        stats[final_stat_name].prefix = prefix


def common_function_pattern(stats, pattern, name_list=[], prefix='', suffix=''):
    tmp_stats = {}
    reg = re.compile(pattern)
    for stat_name in stats:
        results = reg.findall(stat_name)
        if results:
            if pattern.endswith('_q\d+'):
                tmp_name = stat_name[:-3]
            else:
                tmp_name = stat_name
            if (name_list and tmp_name in name_list) or (not name_list):
                add_to_tmp_stats(tmp_stats, tmp_name, stats[stat_name], prefix=prefix, suffix=suffix)
    return tmp_stats


def warp_cant_issue(stats):
    return common_function_pattern(stats, "warp_cant_issue_(.*)", node_name_map_counter.keys(), suffix=' of no-issue cycles')


def pipe_utilization(stats):
    """
    This function is used to filter the pipe_utilization counters
    """
    return common_function_pattern(stats, r"^pipe_(.*)", node_name_map_counter.keys(), prefix='active ', suffix=' of total cycles')


def instruction_distribution(stats):
    """
    This function is used to collect the instruction distributions. The raw counters are like inst_executed_XX_ops_qX.
    """
    return common_function_pattern(stats, r"inst_executed_op_(.+?)", suffix=' of all inst')


def cant_dispatch(stats):
    return common_function_pattern(stats, r"cant_dispatch_(.*)", node_name_map_counter.keys(), suffix=" of dispatch stalls")

def barrier(stats):
    tmp_stats = {}
    add_to_tmp_stats(tmp_stats, "block_size", )


def preface_mem_stats(stats, memory_metrics):
    # common stuff
    elapsedClocks = stats['elapsedClocks'].value
    l1_hitrate_stat = stats['l1tex_hit_rate']
    memory_metrics.l1_hit_rate = l1_hitrate_stat.value / 100

    l1_miss_rate = 1 - l1_hitrate_stat.value / 100
    memory_metrics.l1_miss_rate = l1_miss_rate
    
    memory_metrics.lpl1 = stats["l1_lines_per_instruction_avg"].value

    # calculate average bytes per requests and total lds
    total_lds = 0
    lds_stats = {}
    for stat_name in stats:
        # if stat_name.startswith("inst_mem_gld") or stat_name.startswith("inst_mem_geld") or stat_name.startswith(
        #        "inst_mem_ldgsts"):
        if stat_name.startswith("inst_mem_gld") or stat_name.startswith("inst_mem_geld"):
            add_to_tmp_stats(lds_stats, stat_name, stats[stat_name])
            total_lds += int(stats[stat_name].value)
    memory_metrics.total_lds = total_lds

    ggeld_line_reg = re.compile(r"inst_mem_(gld)?(geld)?_(\d+)b")
    sum_requests = 0
    sum_bytes = 0
    for stat_name in lds_stats:
        line_byte = 0
        line_requests = 0
        result0 = ggeld_line_reg.findall(stat_name)
        if result0 and (result0[0] != '' or result0[1] != ''):
            line_byte = int(result0[0][2]) / 8
            line_requests = lds_stats[stat_name].value
        sum_requests += line_requests
        sum_bytes += line_byte * line_requests

    # bytes per l1 instruction
    if sum_requests == 0:
        bpl1 = 0
    else:
        bpl1 = sum_bytes / sum_requests
    memory_metrics.bpl1 = bpl1
    # within_load_coalescing_rate
    high_l1_lines_per_instruction = config.warp_size * \
                                    bpl1 / config.BYTES_PER_L1_INSTRUCTION

    l1_lines_per_load_stat = stats["l1_lines_per_instruction_avg"]
    memory_metrics.l1_lines_per_load = l1_lines_per_load_stat.value

    within_load_coalescing_ratio = config.warp_size * \
                                              high_l1_lines_per_instruction / l1_lines_per_load_stat.value
    memory_metrics.within_load_coalescing_ratio = within_load_coalescing_ratio

    l1_RPC = memory_metrics.total_lds / elapsedClocks
    memory_metrics.l1_RPC = l1_RPC
    
    # utlb miss rate
    utlb_miss_rate = stats['ltp_utlb_miss'].value / (stats['ltp_utlb_hit'].value + stats['ltp_utlb_miss'].value)
    memory_metrics.utlb_miss_rate = utlb_miss_rate
    
    utlb_requests = stats['ltp_utlb_hit'].value + stats['ltp_utlb_miss'].value
    utlb_request_per_clock = utlb_requests / elapsedClocks
    memory_metrics.utlb_RPC = utlb_request_per_clock
    
    # utlb_arb_stall
    utlb_arb_stall_rate = 1
    memory_metrics.utlb_arb_stall_rate = utlb_arb_stall_rate

    # across_load_coalescing_ratio
    across_load_coalescing_ratio = stats["gnic_lg_read_requests_precoalescing"].value / \
                                             stats["gnic_lg_read_requests_postcoalescing"].value
    memory_metrics.across_load_coalescing_ratio = across_load_coalescing_ratio
    # l2 miss rate
    l2_miss_rate = 1 - stats["l2_hit_rate"].value / 100
    memory_metrics.l2_miss_rate = l2_miss_rate
    
    l2_bank_conflict_stat = stats['l2_bank_conflict']
    l2_data_bank_accesses_stat = stats['l2_data_bank_accesses']
    l2_bank_conflict_rate = l2_bank_conflict_stat.value / l2_data_bank_accesses_stat.value
    memory_metrics.l2_bank_conflict_rate = l2_bank_conflict_rate

    if(stats['fb_accesses_per_activate'].value != -1):
        memory_metrics.access_per_activate = stats['fb_accesses_per_activate'].value
    
    if(stats['average_dram_banks'].value != -1):
        memory_metrics.average_dram_banks = stats['average_dram_banks'].value


def add_l1_stats(l1_stats, stats, memory_metrics):
    # hit rate
    l1_hitrate_stat_new = Stat()
    l1_hitrate_stat_new.value = memory_metrics.l1_hit_rate
    add_to_tmp_stats(l1_stats, "l1_hit_rate", l1_hitrate_stat_new)
    # conflicts
    gld_set_conflicts_stat = stats["global_ld_set_conflicts"]
    gld_set_accesses = stats["global_ld_set_accesses"]
    if gld_set_conflicts_stat and gld_set_accesses.value != 0:
        l1_conflict_rate = Stat()
        l1_conflict_rate.value = gld_set_conflicts_stat.value / gld_set_accesses.value
        add_to_tmp_stats(l1_stats, "l1_conflict_rate", l1_conflict_rate)
        memory_metrics.l1_conflict_rate = l1_conflict_rate.value
    # requests per clock, RPC
    #number_of_RPC = Stat()
    #number_of_RPC.value = memory_metrics.l1_RPC
    #add_to_tmp_stats(l1_stats, "l1_RPC", number_of_RPC)
    # lines per load
    add_to_tmp_stats(l1_stats, "l1_lines_per_load", stats["l1_lines_per_instruction_avg"])
    # number of average bytes per load
    bytes_per_load_stat = Stat()
    bytes_per_load_stat.value = memory_metrics.bpl1
    add_to_tmp_stats(l1_stats, "bytes_per_load", bytes_per_load_stat)
    #coalescing
    within_load_coalescing_ratio_stat = Stat()
    within_load_coalescing_ratio_stat.value = memory_metrics.within_load_coalescing_ratio
    add_to_tmp_stats(l1_stats, "within_load_coalescing_ratio", within_load_coalescing_ratio_stat)

def add_utlb_stats(utlb_stats, stats, memory_metrics):
    # l1 miss rate
    l1_miss_rate_stat = Stat()
    l1_miss_rate_stat.value = memory_metrics.l1_miss_rate
    add_to_tmp_stats(utlb_stats, "l1_miss_rate", l1_miss_rate_stat)
    # requests per clock. req: ltpX_utlb_hit+miss
    #utlb_request_per_clock_stat = Stat()
    #utlb_request_per_clock_stat.value = memory_metrics.utlb_RPC
    #add_to_tmp_stats(utlb_stats, 'utlb_RPC', utlb_request_per_clock_stat)

def add_l1tlb_stats(l1tlb_stats, stats, memory_metrics):
    # utlb miss
    utlb_miss_rate_stat = Stat()
    utlb_miss_rate_stat.value = memory_metrics.utlb_miss_rate
    add_to_tmp_stats(l1tlb_stats, "utlb_miss_rate", utlb_miss_rate_stat)
    # utlb_arb_stall
    utlb_arb_stall_stat = Stat()
    utlb_arb_stall_stat.value = memory_metrics.utlb_arb_stall_rate
    add_to_tmp_stats(l1tlb_stats, "utlb_arb_stall_rate", utlb_arb_stall_stat)

def add_l2_stats(l2_stats, stats, memory_metrics):
    # coalescing ratio
    across_load_coalescing_ratio_stat = Stat()
    across_load_coalescing_ratio_stat.value = memory_metrics.across_load_coalescing_ratio
    add_to_tmp_stats(l2_stats, "across_load_coalescing_ratio", across_load_coalescing_ratio_stat)
    # conflicts
    l2_bank_conflict_rate_stat = Stat()
    l2_bank_conflict_rate_stat.value = memory_metrics.l2_bank_conflict_rate
    add_to_tmp_stats(l2_stats, "l2_bank_conflict_rate", l2_bank_conflict_rate_stat)

def add_fb_stats(fb_stats, stats, memory_metrics):
    l2_miss_rate_stat = Stat()
    l2_miss_rate_stat.value = memory_metrics.l2_miss_rate
    add_to_tmp_stats(fb_stats, "l2_miss_rate", l2_miss_rate_stat)
    
    # access per activate. Ideal value is 16.
    if(memory_metrics.access_per_activate is not None):
        fb_accesses_per_activate_stat = stats['fb_accesses_per_activate']
        add_to_tmp_stats(fb_stats, "fb_accesses_per_activate", fb_accesses_per_activate_stat)

    if(memory_metrics.average_dram_banks is not None):
        add_to_tmp_stats(fb_stats, "average_dram_banks", stats['average_dram_banks'])

    # compression rate
    if memory_metrics.compress_rate is not None:
        successful_compressions_stat = Stat('compression_success_rate', 'plc_total_successes/plc_total_evaluations')
        successful_compressions_stat.value = memory_metrics.compress_rate
        add_to_tmp_stats(fb_stats, "compression_success_rate", successful_compressions_stat)
    
    if(stats['dram_turns'].value > 5):
        add_to_tmp_stats(fb_stats, "dram_turns", stats['dram_turns'])
    if(stats['dram_noReq'].value > 5):
        add_to_tmp_stats(fb_stats, "dram_noReq", stats['dram_noReq'])

def long_scoreboard_throughput(stats, memory_metrics):
    preface_mem_stats(stats, memory_metrics)

    # L1 throughput
    l1_throughput = (1 - memory_metrics.l1_miss_rate) * memory_metrics.total_lds * \
                    memory_metrics.bpl1 * config.L1_THROUGHPUT_FIX

    # l1_lines_per_instruction
    utlb_throughput = memory_metrics.l1_miss_rate * \
                      (1 - memory_metrics.utlb_miss_rate) * memory_metrics.lpl1 * config.uTLB_THROUGHPUT_FIX
    # l1 TLB miss rate
    gpcl1_tlb_miss = stats["gpcl1_tlb_miss"].value
    gpcl1_tlb_hit = stats["gpcl1_tlb_hit"].value
    # All requests hit in utlb is possible.
    if gpcl1_tlb_hit + gpcl1_tlb_miss == 0:
        print('No global load instruction.')
        l1_tlb_miss_rate = 0
    else:
        l1_tlb_miss_rate = gpcl1_tlb_miss / (gpcl1_tlb_hit + gpcl1_tlb_miss)
    l1_tlb_throughput = memory_metrics.l1_miss_rate * memory_metrics.utlb_miss_rate * \
                        (1 - l1_tlb_miss_rate) * memory_metrics.lpl1 * config.L1_TLB_THROUGHPUT_FIX
    # l2
    gnic_read_sectors_postcoalescing = stats['gnic_read_sectors_postcoalescing'].value
    # bytes of L2 instructions
    bl2 = config.BYTES_PER_L2_INSTRUCTION * gnic_read_sectors_postcoalescing
    l2_throughput = (1 - memory_metrics.l2_miss_rate) * bl2 * config.L2_THROUGHPUT_FIX
    fb_bytes = stats["fb_total_bytes"].value
    fb_throughput = fb_bytes * config.FB_THROUGHPUT_FIX

    # find the bottleneck
    adict = {"l1": l1_throughput, "utlb": utlb_throughput,
             "l1tlb": l1_tlb_throughput, "l2": l2_throughput, "fb": fb_throughput}
    list1 = sorted(adict.items(), key=lambda x: x[1])
    bottleneck_unit = list1[-1][0]
    bottleneck_count = float(list1[-1][1])
    memory_metrics.throughputs = adict
    bottleneck_stats = None

    # always fill memory metrics for everyone
    l1_stats = {}
    add_l1_stats(l1_stats, stats, memory_metrics)
    if bottleneck_unit == 'l1':
        bottleneck_stats = l1_stats
        memory_metrics.bottleneck = "l1"

    utlb_stats = {}
    add_utlb_stats(utlb_stats, stats, memory_metrics)
    if bottleneck_unit == 'utlb':
        bottleneck_stats = utlb_stats
        memory_metrics.bottleneck = "tlb"

    l1tlb_stats = {}
    add_l1tlb_stats(l1tlb_stats, stats, memory_metrics)
    if bottleneck_unit == 'l1tlb':
        bottleneck_stats = l1tlb_stats
        memory_metrics.bottleneck = "tlb"

    l2_stats = {}
    add_l2_stats(l2_stats, stats, memory_metrics)
    if bottleneck_unit == 'l2':
        bottleneck_stats = l2_stats
        memory_metrics.bottleneck = "l2"

    # FB
    fb_stats = {}
    add_fb_stats(fb_stats, stats, memory_metrics)
    if bottleneck_unit == 'fb':
        bottleneck_stats = fb_stats
        memory_metrics.bottleneck = "fb"

    util_stat = Stat()
    util_stat.value = bottleneck_count / stats['elapsedClocks'].value
    add_to_tmp_stats(bottleneck_stats, "util_rate", util_stat)
    return bottleneck_unit, bottleneck_stats, memory_metrics


def long_scoreboard_latency(stats, memory_metrics):
    latency_stats = {}
    sum_latency = 0
    l1_miss_rate = memory_metrics.l1_miss_rate
    # L1
    ld_div_rif = 1
    total = 0
    # lines_per_instruction
    lpl1 = stats["l1_lines_per_instruction_avg"].value
    l1_latency = config.L1_LATENCY_FIX + 2 * (lpl1 - 1)
   
    latency_stats["l1_cycles"] = Stat(aname='l1_cycles', avalue=int(np.ceil(l1_latency)))
    l1_latency_stat_value = int(np.ceil(ld_div_rif * l1_latency))
    sum_latency += l1_latency_stat_value
    latency_stats["l1_latency"] = Stat(aname='l1_latency', avalue=l1_latency_stat_value)
    
    #tlb
    if(stats['mmu_ack_latency'].value != -1):
        raw_tlb_latency = stats['mmu_ack_latency'].value
        tlb_latency = int(np.ceil(l1_miss_rate * ld_div_rif * stats['mmu_ack_latency'].value))
    else:
        #utlb
        utlb_latency = config.uTLB_LATENCY_FIX + (lpl1 - 1)
        raw_tlb_latency = utlb_latency
        tlb_latency = int(np.ceil(l1_miss_rate * ld_div_rif * utlb_latency))
        # L1 TLB
        l1tlb_latency = config.l1TLB_LATENCY_FIX + lpl1 - 1
        raw_tlb_latency += l1tlb_latency
        utlb_miss_rate = memory_metrics.utlb_miss_rate
        tlb_latency += int(np.ceil(l1_miss_rate * utlb_miss_rate * ld_div_rif * l1tlb_latency))
    
    latency_stats["tlb_cycles"] = Stat(aname='tlb_cycles', avalue=int(np.ceil(raw_tlb_latency)))
    tlb_latency_stat_value = tlb_latency
    sum_latency += tlb_latency_stat_value
    latency_stats["tlb_latency"] = Stat(aname='tlb_latency', avalue=tlb_latency_stat_value)
    # L2
    # coalescing rate
    if(stats['gnic_latency'].value != -1):
        l2_latency = stats['gnic_latency'].value - memory_metrics.l2_miss_rate * stats['average_latency_reads'].value
    else:
        l2_latency = config.l2_latency
    
    latency_stats["l2_cycles"] = Stat(aname='l2_cycles', avalue=int(np.ceil(l2_latency)))
    l2_cycle_stat_value = int(np.ceil(l1_miss_rate * ld_div_rif * l2_latency /
                                      memory_metrics.across_load_coalescing_ratio))
    sum_latency += l2_cycle_stat_value
    latency_stats["l2_latency"] = Stat(aname='l2_latency', avalue=l2_cycle_stat_value)
    # FB
    if(stats['average_latency_reads'].value != -1):
        fb_latency = stats["average_latency_reads"].value
    else:
        fb_latency = config.fb_latency
    
    latency_stats["fb_cycles"] = Stat(aname='fb_cycles', avalue=int(np.ceil(fb_latency)))
    fb_cycle_stat_value = int(np.ceil(l1_miss_rate * memory_metrics.l2_miss_rate * ld_div_rif * fb_latency /
                                      memory_metrics.across_load_coalescing_ratio))
    sum_latency += fb_cycle_stat_value
    latency_stats["fb_latency"] = Stat(aname='fb_latency', avalue=fb_cycle_stat_value)

    latency_stats["total_latency"] = Stat(aname='total_latency', avalue=sum_latency)
    return latency_stats
