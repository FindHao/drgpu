from data_struct import Node
from data_struct import SOURCE_CODE_NODE
from data_struct import config
from gather import find_node
import numpy as np


class Source_Code_Line:
    def __init__(self, raw_line='', line_number=-1, file_name=''):
        self.raw_line = raw_line
        self.line_number = line_number
        self.file_name = file_name


stalls_mapping_to_detail_report = {
    "stall_barrier": "warp_cant_issue_barrier",
    "stall_dispatch": "warp_cant_issue_dispatch",
    "stall_drain": "warp_cant_issue_drain",
    "stall_imc": "warp_cant_issue_imc_miss",
    "stall_lg": "warp_cant_issue_lg_throttle",
    "stall_long_sb": "warp_cant_issue_long_scoreboard",
    "stall_math": "warp_cant_issue_pipe_throttle",
    "stall_membar": "warp_cant_issue_membar",
    "stall_mio": "warp_cant_issue_mio_throttle",
    "stall_misc": "warp_cant_issue_misc",
    "stall_no_inst": "warp_cant_issue_no_inst",
    # "stall_not_selected": "",
    # "stall_selected": "",
    "stall_short_sb": "warp_cant_issue_short_scoreboard",
    # "stall_sleep": "",
    # "stall_tex": "",
    "stall_wait": "warp_cant_issue_wait",
}


def add_one_source_code_node(target_node: Node, content, prefix=''):
    s_node = Node("source_code_for_%s_%d" % (target_node.name, len(target_node.child)))
    s_node.type = SOURCE_CODE_NODE
    s_node.suffix_label = content
    s_node.prefix_label = prefix
    target_node.child.append(s_node)


def add_source_code_nodes(tmpstats, hw_tree, analysis):
    stall_sass_code = analysis.stall_sass_code
    lines = analysis.source_lines
    for stat_name in tmpstats:
        cur_node = find_node(hw_tree, stat_name)
        if not cur_node:
            continue
        stall_sass_code_clean = [a for a in stall_sass_code[stat_name].items() if not np.isnan(a[1])]
        # sort all instructions leading to this stall reason by their counts
        stall_insts = sorted(stall_sass_code_clean, key=lambda kv: (kv[1], kv[0]), reverse=True)
        sum_value = sum(a[1] for a in stall_insts)
        if sum_value == 0:
            continue
        N = config.max_number_of_showed_source_code_nodes
        while sum(a[1] for a in stall_insts[:N]) > config.max_percentage_of_showed_nodes * sum_value and N != 1:
            N -= 1
        content = ''
        new_sum = sum(a[1] for a in stall_insts[:N])
        last_file_name = ''
        for inst_count in stall_insts[:N]:
            cur_inst:Source_Code_Line = lines[inst_count[0]]
            if cur_inst.file_name != last_file_name:
                content += str(cur_inst.file_name) + r':\l'
                last_file_name = cur_inst.file_name
            content += r"%d %s    %.2f%%\l" % (cur_inst.line_number, cur_inst.raw_line, inst_count[1] / new_sum * 100)
        add_one_source_code_node(cur_node, content)
