"""
This file contains main class structures for some terms.
"""
import re

NORMAL_TREE_NODE = 0
SUGGESTION_NODE = 1
SOURCE_CODE_NODE = 2
LATENCY_NODE = 3
SHOW_AS_RAW_VALUE = 0
SHOW_AS_PERCENTAGE = 1
VALUE_TYPE_INT = 0
VALUE_TYPE_FLOAT = 1
# The value is float but has percentage meaning
VALUE_TYPE_PERCENTAGE = 2
# highlight this path in final memory latency branch
MEMORY_LATENCY_HIERARCHY = [('avg_latency', 'l1_latency'), ('l1_latency', 'tlb_latency'), ('tlb_latency', "l2_latency"),
                            ('l2_latency', 'fb_latency')]


class Report:
    def __init__(self, path='', source_report_path='', kernel_id=0):
        self.path = path
        self.source_report_path = source_report_path
        # {unit_name: Unit, }
        self.units = {}
        # kernel id in ncu csv report
        self.kernel_id = kernel_id


class Analysis:
    def __init__(self):
        # {stat_name: stat, } type:{str: Stat}
        self.all_stats = {}
        # {stall_reason: {inst line number: count, }, }
        self.stall_sass_code = {}
        # [None, inst1, inst2, ]
        self.source_lines = []


class Unit:
    def __init__(self, name=''):
        self.name = name
        # {name: Stat, }
        self.stats = {}

    def find_stat(self, find_name):
        return self.stats.get(find_name, None)

    def find_stat_return_0(self, find_name):
        return self.stats.get(find_name, 0)

    # testing function
    def find_stat_similar(self, find_name):
        exact = self.find_stat(find_name)
        if exact:
            return exact
        reg = re.compile(r".*%s.*" % find_name)
        stat_names = self.stats.keys()
        similars = {}
        for stat_name in stat_names:
            result = reg.findall(stat_name)
            if result:
                similars[stat_name] = self.stats.get(stat_name)
        return similars


class Stat:
    def __init__(self, aname='', araw_name='', avalue=0):
        self.name = aname
        self.raw_name = araw_name
        # todo: every stat's default value is 0?
        self.value = avalue
        self.value_type = None
        self.suffix = ''
        self.prefix = ''
        self.avg = 0
        self.min = None
        self.max = None
        # There may be multiple max and min. So max_sm should be a list.
        self.max_sm = None
        self.min_sm = None
        self.stdDev = 0
        self.utilization = None
        # {sm6_1_1: (content, cycles, validity), }
        self.SMs_raw_value = {}
        # {sm6_1_1: value, }
        self.SMs_value = {}
        self.expression_raw = ""
        self.expression_pattern = ""
        self.description = ""
        # In the report, every stat has 3 attributes. The final value it showed in NVPDM is not sure wether it is content or cycles.
        self.content = 0
        self.validity = ''
        self.cycles = 0

    def merge(self, bstat):
        """Use this function to merge q0-q3"""
        self.value += bstat.value
        # @todo belowing has bugs. That may be caused by different gpu has different number of SMs. 
        # for sm in bstat.SMs_raw_value:
        #     b_tuple = bstat.SMs_raw_value[sm]
        #     #@ todo there is a bug
        #     a_tuple = self.SMs_raw_value[sm]
        #     # The last one is the validity. Should I ignore it?
        #     new_tuple = (a_tuple[0] + b_tuple[0],
        #                  a_tuple[1] + b_tuple[1], a_tuple[2])
        #     self.SMs_raw_value[sm] = new_tuple
        # for sm in bstat.SMs_value:
        #     b = bstat.SMs_value[sm]
        #     a = self.SMs_value[sm]
        #     self.SMs_value[sm] = a+b
        self.content += bstat.content
        if self.cycles is not None and bstat.cycles is not None:
            self.cycles += bstat.cycles
        # self.find_extrem_sm()

    def find_extrem_sm(self):
        if not self.SMs_value:
            print("SMs_value is empty")
            return
        tmp_max_v = max(self.SMs_value.values())
        tmp_max_sms = [
            _ for _ in self.SMs_value if self.SMs_value[_] == tmp_max_v]
        tmp_min_v = min(self.SMs_value.values())
        tmp_min_sms = [
            _ for _ in self.SMs_value if self.SMs_value[_] == tmp_min_v]


class Node:
    """"""

    def __init__(self, aname, atype=NORMAL_TREE_NODE):
        """If the node is suggestion node, the stat would be empty."""
        self.name = aname
        self.percentage = None
        # add content after percentage
        self.suffix_label = ''
        self.prefix_label = ''
        self.child = []
        # 0: normal tree node
        # 1: suggestion node
        self.type = atype
        # 0: show as raw value
        # 1: show as percentage 
        self.show_percentage_or_value = SHOW_AS_PERCENTAGE


class Memory_Metrics:
    def __init__(self):
        self.bottleneck = None
        self.total_lds = None
        self.l1_hit_rate = None
        self.l1_miss_rate = None
        self.lpl1 = None
        self.bpl1 = None
        self.within_load_coalescing_ratio = None
        self.across_load_coalescing_ratio = None
        self.l1_conflict_rate = None
        self.l1_RPC = None
        self.l1_lines_per_instruction = None

        self.utlb_RPC = None
        self.utlb_miss_rate = None
        self.utlb_arb_stall_rate = None

        self.l2_miss_rate = None
        self.l2_bank_conflict_rate = None
        self.l2_RPC = None
        self.throughputs = {}

        self.access_per_activate = None
        self.compress_rate = None
        self.average_dram_banks = None

        self.shared_ld_conflict_per_request = None
        self.shared_st_conflict_per_request = None


class Configuration:
    def __init__(self):
        self.warp_size = None
        self.quadrants_per_SM = None
        self.max_number_of_showed_nodes = None
        self.max_percentage_of_showed_nodes = None
        # XX_q1, _q2 the last 3 char will be removed.
        self.number_of_suffix = 3
        self.L1_THROUGHPUT_FIX = None
        self.uTLB_THROUGHPUT_FIX = None
        self.L1_TLB_THROUGHPUT_FIX = None
        self.BYTES_PER_L2_INSTRUCTION = None
        self.L2_THROUGHPUT_FIX = None
        self.FB_THROUGHPUT_FIX = None
        self.BYTES_PER_L1_INSTRUCTION = None
        self.conflict_high_threshold = None
        self.low_activewarps_per_activecycle = None
        self.L1_THROUGHPUT_PEAK = None
        self.high_l1_throughput = None
        self.high_l1_hit_rate = None
        self.high_l1_conflict_rate = None
        self.low_access_per_activate = None
        self.low_bank_per_access = None
        self.within_load_coalescing_ratio = None
        self.low_l1_hit_rate = None
        self.high_utlb_miss_rate = None
        self.high_l2_miss_rate = None
        self.high_l2_bank_conflict_rate = None
        self.high_not_predicated_off_thread_per_inst_executed = None
        self.max_not_predicated_off_thread_per_inst_executed = None
        self.low_compress_rate = None
        self.L1_LATENCY_FIX = None
        self.uTLB_LATENCY_FIX = None
        self.l1TLB_LATENCY_FIX = None
        self.l2_latency = None
        self.fb_latency = None
        self.max_percentage_of_showed_source_code_nodes = None
        self.max_number_of_showed_source_code_nodes = None
        self.max_avtive_warps_per_SM = None
        self.compute_capability = None


node_name_map_counter = {
    "Idle": "No-issue cycles",
    # warp_cant_issue_
    "warp_cant_issue_barrier": "CTA (Block) waiting at barriers",
    "warp_cant_issue_branch_resolving": "Delay due to branch evaluation",
    "warp_cant_issue_dispatch": "Delay due to dispatch stall",
    "warp_cant_issue_drain": "Delay due to pending global stores before exit",
    "warp_cant_issue_imc_miss": "Delay due to constant cache accesses",
    "warp_cant_issue_lg_credit_throttle": r"Delay in issuing global memory loads",
    "warp_cant_issue_long_scoreboard": r"Delay due to global memory accesses",
    "warp_cant_issue_membar": "Threads waiting for memory barriers",
    "warp_cant_issue_mio_throttle": r"Delay in issuing shared memory accesses",
    "warp_cant_issue_misc": "Miscellaneous",
    "warp_cant_issue_no_inst": "No Instructions",
    "warp_cant_issue_pipe_throttle": "Delay due to pipe contention",
    "warp_cant_issue_short_scoreboard": r"Delay due to shared memory accesses",
    "warp_cant_issue_ttu_long_scoreboard": r"Delay due to Tree Traversal Unit (TTU) Instructions",
    "warp_cant_issue_ttu_ticket_pending": r"Delay due to Tree Traversal Unit (TTU) Ticket Pending",
    "warp_cant_issue_wait": r"Delay due to dependent instructions/issue rate",  # instr dist
    # pipe
    "adu_pipe_utilization": "Address divergence pipe",
    "alu_pipe_utilization": "Integer and logic pipe",
    "cbu_pipe_utilization": "Barrier, convergence, and branch pipe",
    "lsu_pipe_utilization": "Load store pipe",
    "xu_pipe_utilization": "Special functions pipe",
    "fma_pipe_utilization": "FP32 and IMA pipe",
    "fma64lite_pipe_utilization": "FP64 pipe",
    "mma_pipe_utilization": "MMA pipe",

    "pipe_adu": "Address divergence pipe",
    "pipe_alu": "Integer and logic pipe",
    "pipe_cbu": "Barrier, convergence, and branch pipe",
    "pipe_ipa": "IPA",
    "pipe_lsu": "Load store pipe",
    "pipe_xu": "Special functions pipe",
    "pipe_fma": "FP32 and IMA pipe",
    "pipe_fp64": "FP64 pipe",
    "pipe_tensor_fp64": "DMMA pipe",
    "pipe_tensor_int": "HMMA pipe",
    "pipe_tensor_fp": "IMMA pipe",
    "pipe_tex": "tex",
    "pipe_uniform": "uniform",

    "cant_dispatch_high_power_throttle": "high power",
    "cant_dispatch_register_read_f": "register read non-MMA",
    "cant_dispatch_register_read_m": "register read MMA",
    "cant_dispatch_register_write": "register write",
    "cant_dispatch_others": "others",
    # less important can't dispatch
    "cant_dispatch_uniform_register_read": "register read uniform",
    "cant_dispatch_mask_ram_write": "mask ram write",
    "cant_dispatch_pred_write": "pred write",
    "cant_dispatch_power_irt_throttle": "power irt",
    "cant_dispatch_power_vat_throttle": "power vat",

    "inst_executed_op_bit": "bit",
    "inst_executed_op_control": "control",
    "inst_executed_op_conversion": "conversion",
    "inst_executed_op_fp16": "FP16",
    "inst_executed_op_fp32": "FP32",
    "inst_executed_op_fp64": "FP64",
    "inst_executed_op_integer": "integer",
    "inst_executed_op_inter_thread_communication": "inter_thread_communication",
    "inst_executed_op_memory": "memory",
    "inst_executed_op_misc": "misc",
    "inst_executed_op_uniform": "uniform",

    "inst_executed_op_bar": "barrier",
    "inst_executed_op_branch": "branch",
    "inst_executed_op_convert32": "convert FP32",
    "inst_executed_op_convert64": "convert FP64",
    "inst_executed_op_imad": "IMAD",
    "inst_executed_op_ipa": "IPA",
    "inst_executed_op_mufu": "MUFU",
    "inst_executed_op_bmma": "Bit MMA",
    "inst_executed_op_imma": "Int MMA",
    "inst_executed_op_dmma": "FP64 MMA",

    "inst_mem_gld_32b": "global ld 32b",
    "inst_mem_gld_64b": "global ld 64b",
    "inst_mem_gld_128b": "global ld 128b",
    "inst_mem_geld_32b": "generic ld 32b",
    "inst_mem_geld_64b": "generic ld 64b",
    "inst_mem_geld_128b": "generic ld 128b",
    "inst_mem_ldgsts_32b": "ldgsts ld 32b",
    "inst_mem_ldgsts_64b": "ldgsts ld 64b",
    "inst_mem_ldgsts_128b": "ldgsts ld 128b",
    "inst_mem_shared_ld_32b": "shared ld 32b",
    "inst_mem_shared_ld_64b": "shared ld 64b",
    "inst_mem_shared_ld_128b": "shared ld 128b",
    "inst_mem_shared_st_32b": "shared st 32b",
    "inst_mem_shared_st_64b": "shared st 64b",
    "inst_mem_shared_st_128b": "shared st 128b",

    "concurrent_warps": "#concurrent warps/SM",

    "mio_shared_ld_conflict": "Conflicts per shared load",
    "short_shared_ld_conflict": "Conflicts per shared load",
    "short_shared_st_conflict": "Conflicts per shared store",

    "throughput_l1": "L1",
    "throughput_utlb": "uTLB",
    "throughput_l1tlb": "L1TLB",
    "throughput_l2": "L2",
    "throughput_fb": "FB/DRAM",

    "avg_latency": "Latency distribution per request",
    "lg_latency": "Average load global latency",
    "generic_latency": "Average load generic latency",
    "l1_latency": "L1 latency contribution",
    "tlb_latency": "TLB latency contribution",
    "l2_latency": "L2 latency contribution",
    "fb_latency": "FB/DRAM latency contribution",
    "total_latency": "Total memory latency",

    "l1_hit_rate": "L1 hit rate",
    "l1_hit_with_under_miss_rate": "L1 hit + hit under miss rate",
    "l1_conflict_rate": "Set conflicts",
    "l1_RPC": "L1 requests per clock",
    "l1_lines_per_load": "Lines per request",
    "bytes_per_load": "Bytes per request",

    "l1_miss_rate": "L1 miss rate",
    "utlb_RPC": "Request per clock",

    "utlb_miss_rate": "Utlb miss rate",
    "utlb_arb_stall_rate": "Utlb-L1 stall rate",

    "l2_hit_rate": "L2 hit rate",
    "within_load_coalescing_ratio": "Intra-req coalescing ratio",
    "across_load_coalescing_ratio": "Across-req coalescing ratio",
    "l2_bank_conflict_rate": "L2 bank conflict rate",
    "l2_RPC": "L2 requests per clock",

    "l2_miss_rate": "L2 miss rate",
    "fb_accesses_per_activate": "Accesses per turn",
    "average_dram_banks": "Avg DRAM banks accessed",
    "fb_total_bytes": "DRAM bytes",
    "compression_success_rate": "PLC compression rate",
    "dram_util": "DRAM utilization",
    "dram_throughput": "DRAM achieved bandwidth",
    "dram_noReq": "%cycles lost due to no DRAM requests",
    "dram_turns": "%cycles lost due to DRAM R2W/W2R turns",
}

config = Configuration()
memory_metrics = Memory_Metrics()
