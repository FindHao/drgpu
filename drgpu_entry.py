#!/bin/python3
from gather import *
import argparse
import os
from unit_hunt import *
from dot_graph import *
from suggestions import *

from read_reports import *
from source_code_analysis import add_source_code_nodes


def work(report, dot_graph_name, memoryconfig):
    global memory_metrics
    read_config(memoryconfig, config)

    analysis = Analysis()
    # {stat_name: stat, } type:{str: Stat}
    all_stats = analysis.all_stats
    if dot_graph_name is None:
        (_, dot_graph_name) = os.path.split(report.path)
        (dot_graph_name, _) = os.path.splitext(dot_graph_name)
    # read reports and filter all useful stats
    fill_stats(all_stats, report)
    if report.source_report_path:
        fill_source_report(report, analysis)

    hw_tree = Node('Idle')
    hw_tree.suffix_label = ' of total cycles'
    retireIPC = all_stats.get('retireIPC', None)
    if retireIPC:
        root_percentage = retireIPC.value / config.quadrants_per_SM
    else:
        print("Could not get stat retireIPC")
        root_percentage = 0
    hw_tree.percentage = 1 - root_percentage

    hw_tree.prefix_label = get_kernel_name(all_stats['kernel_name'].value) + "\n"
    hw_tree.suffix_label = ''
    best_possible = 100 * (
            1.0 - 1.0 / (np.ceil(all_stats['activewarps_per_activecycle'].value / config.quadrants_per_SM)))
    hw_tree.suffix_label += r" (lowest possible: %i%% for %i active warps)" % (
        best_possible, all_stats['activewarps_per_activecycle'].value)
    max_val = 0
    sol_unit = ""
    for unit in ['SM', 'L1', 'L2', 'Dram', 'Compute_Memory']:
        next_val = all_stats['sol_' + unit.lower()].value
        if next_val > max_val:
            sol_unit = unit
            max_val = next_val
    hw_tree.suffix_label += r"\nUtil/SOL: %.2f%% (%s)" % (max_val, sol_unit)

    hw_tree.suffix_label += r"\nIssue IPC: %.2f" % (all_stats["issueIPC"].value)

    # first level
    tmpstats = warp_cant_issue(all_stats)
    add_sub_branch(tmpstats, hw_tree, 1)
    if report.source_report_path is not None:
        add_source_code_nodes(tmpstats, hw_tree, analysis)

    # pipe utilization is the subbranch of shadow_pipe_throttle
    tmpstats = pipe_utilization(all_stats)
    target_node = find_node(hw_tree, "warp_cant_issue_pipe_throttle")
    if not target_node:
        print("Could not find the target node: warp_cant_issue_pipe_throttle")
    else:
        add_pipe_throttle_branch(tmpstats, target_node)

    # instruction distribution is the subbranch of wait
    tmpstats = instruction_distribution(all_stats)
    target_node = find_node(hw_tree, "warp_cant_issue_wait")
    if not target_node:
        print("Could not find the target node: warp_cant_issue_wait")
    else:
        add_sub_branch(tmpstats, target_node, 1)

    # warp_cant_issue_dispatch_stall
    tmpstats = cant_dispatch(all_stats)
    target_node = find_node(hw_tree, "warp_cant_issue_dispatch")
    if not target_node:
        print("Could not find the target node: warp_cant_issue_dispatch")
    else:
        add_sub_branch(tmpstats, target_node, 1)

    target_node = find_node(hw_tree, "warp_cant_issue_lg_throttle")
    if not target_node:
        print("Could not find the target node: warp_cant_issue_lg_throttle")
    else:
        add_lg_throttle_branch(all_stats, target_node)

    # target_node = find_node(hw_tree, "warp_cant_issue_barrier")
    # if not target_node:
    #     print("Could not find the target node: warp_cant_issue_barrier")
    # else:
    #     add_sub_branch(tmpstats, target_node, 1)

    # warp_cant_issue_long_scoreboard memory
    bottleneck_unit, bottleneck_stats, memory_metrics = long_scoreboard_throughput(all_stats, memory_metrics)
    long_scoreboard_node = find_node(hw_tree, "warp_cant_issue_long_scoreboard")
    latency_stats = long_scoreboard_latency(all_stats, memory_metrics)
    add_sub_branch_for_longscoreboard_latency(latency_stats, long_scoreboard_node, all_stats, memory_metrics)
    add_sub_branch_for_longscoreboard_throughput(all_stats, bottleneck_unit, bottleneck_stats, long_scoreboard_node, 1)

    shared_mem_stats = common_function_pattern(all_stats, 'shared_ld_(\d+)b_executed')
    add_shared_memory_info(all_stats, shared_mem_stats, memory_metrics)
    target_node = find_node(hw_tree, "warp_cant_issue_mio_throttle")
    add_branch_for_mio_throttle(all_stats, shared_mem_stats, memory_metrics, target_node)
    target_node = find_node(hw_tree, "warp_cant_issue_short_scoreboard")
    add_branch_for_short_scoreboard(all_stats, shared_mem_stats, memory_metrics, target_node)

    # suggestions part
    pipe_suggest(hw_tree, all_stats)
    barrier_suggest(hw_tree, all_stats)
    branch_solving_suggest(hw_tree, all_stats)
    dispatch_stall_suggest(hw_tree, all_stats)
    drain_suggest(hw_tree, all_stats)
    # imc_miss_suggest(hw_tree, all_stats)
    lg_credit_throttle_suggest(hw_tree, all_stats)
    memory_suggest(hw_tree, all_stats, bottleneck_unit, memory_metrics)
    membar_suggest(hw_tree, all_stats)
    mio_throttle_suggest(hw_tree, all_stats, shared_mem_stats)
    short_scoreboard_suggest(hw_tree, all_stats, shared_mem_stats)
    wait_suggestion(hw_tree, all_stats)

    build_dot_graph(hw_tree, "dots/" + dot_graph_name)
    print("save to dots/" + dot_graph_name + ".svg")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--report-path', metavar='The path of main report.',
                        required=True, dest='report_path', action='store')
    parser.add_argument('-o', '--output', metavar='Set the output file to save decision tree.',
                        required=False, dest='output', action='store')
    parser.add_argument('-s', '--source', metavar='The path of source mapping report from NCU. NCU model only.',
                        required=False, dest='source', action='store')
    parser.add_argument('-c', '--memoryconfig',
                        metavar='The path of memory config file or only file name in mem_config folder',
                        required=False, dest='memoryconfig', action='store')
    parser.add_argument('-id', '--id',
                        metavar='The id of the kernel you want to analyze in exported csv files.',
                        required=False, dest='kernel_id', action='store')
    args = parser.parse_args()
    report_path = args.report_path
    if not args.memoryconfig:
        memoryconfig = sys.path[0] + '/mem_config/gtx1650.ini'
        print(
            "You didn't specify running platform for this report. DrGPU will use gtx1650.ini as default GPU configuration.")
    else:
        memoryconfig = args.memoryconfig
        if not memoryconfig.endswith('.ini'):
            memoryconfig += '.ini'
        if not memoryconfig.startswith('/'):
            memoryconfig = sys.path[0] + "/mem_config/" + memoryconfig
    kernel_id = 0
    if args.kernel_id:
        kernel_id = int(args.kernel_id)
    print(report_path)
    print(args.source)
    report = Report(report_path, args.source, kernel_id)
    work(report, args.output, memoryconfig)
