import gzip
import json
from data_struct import *
import functools
from unit_hunt import add_l1_stats, add_utlb_stats, add_l1tlb_stats
from unit_hunt import add_l2_stats, add_fb_stats


def filter_unit_name(all_names):
    """check wether the instances is match with units"""
    unit_names = []
    unit_instance_names = []
    for name in all_names:
        if not name.endswith('json.gz'):
            print("File %s is not regural json.gz file." % name)
        else:
            if name.endswith('_instances.json.gz'):
                unit_instance_names.append(name[:-len("_instances.json.gz")])
            else:
                unit_names.append(name[:-len(".json.gz")])
    if unit_names != unit_instance_names:
        print("There are some irregular files:")
        difference = (set(unit_instance_names) - set(unit_names)
                      ).union(set(unit_names) - set(unit_instance_names))
        print(list(difference))
    return unit_names


def build_unit(unit_name, path):
    # filter valus in XX.json.gz
    with gzip.open(path + "/" + unit_name + ".json.gz", 'rt', encoding='utf8') as zipfile:
        print("Load ", unit_name, ".json.gz")
        unit_json = json.load(zipfile)
    # >>> unit_json.keys()
    # dict_keys(['Bottlenecks', 'SOL', 'aliases', 'instanceCount', 'instancesSummary', 'interfaces', 'name', 'pm_histogram_data', 'primaryOwnerEmail', 'primaryOwnerName', 'results'])
    # results is what we want. In NVPDM, results are stats, unit view.
    stats = unit_json['results']['stat']
    unit = Unit(unit_name)
    for stat in stats:
        # todo fileter partial hw counters
        astat = Stat()
        astat.raw_name = stat['name']
        astat.content = stat.get('content')
        astat.cycles = stat.get('cycles')
        if astat.content is not None:
            astat.value = astat.content
        else:
            astat.value = astat.cycles

        unit.stats[stat['name']] = astat

    stats = unit_json['SOL']
    max_val = 0
    for instance in stats:
        this_val = float(instance['stat'].get('percent'))
        if this_val > max_val:
            max_val = this_val

    sol_name = unit_name + "_sol"
    astat = Stat()
    astat.raw_name = sol_name
    astat.content = max_val
    astat.cycles = max_val
    astat.value = max_val
    unit.stats[sol_name] = astat

    # filter valus in XX_instances.json.gz 
    # todo check wether the file exists
    # with gzip.open(path + "/" + unit_name + "_instances.json.gz", 'rt', encoding='utf8') as zipfile:
    #    unit_json = json.load(zipfile)
    # instances = unit_json['instances']
    # for instance in instances:
    #    # SMX_X_X
    #    sm_name = instance['name']
    #    for stat in instance['results']['stat']:
    #        astat = unit.stats.get(stat['name'], Stat())
    #        astat.name = stat['name']
    #        astat.SMs_raw_value[sm_name] = (stat.get('content', 0), stat.get('cycles', 0), stat.get('validity', ''))
    #        a = stat.get('content', 0)
    #        if a == 0:
    #            a = stat.get('cycles', 0)
    #        astat.SMs_value[sm_name] = a
    #        unit.stats[stat['name']] = astat
    return unit


def cmp(astat, bstat):
    if bstat.value < astat.value:
        return -1
    elif astat.value < bstat.value:
        return 1
    else:
        return 0


def add_sub_branch(stats, hw_tree, current_percentage, do_percent=True):
    stats_list = list(stats.values())
    sum_value = 0
    for stat in stats_list:
        sum_value += stat.value
        # print(stat.name, stat.value)
    # for debug
    # print(sum_value)
    N = config.max_number_of_showed_nodes
    stats_list_topN = sorted(stats_list, key=functools.cmp_to_key(cmp))[:N]
    while (sum(a.value for a in stats_list_topN[:N]) > config.max_percentage_of_showed_nodes * sum_value) and N > 2:
        N -= 1
    new_sum_value = sum_value
    for stat in stats_list_topN[:N]:
        node = Node(stat.name)
        node.percentage = stat.value / new_sum_value * current_percentage
        if stat.utilization is not None:
            node.suffix_label = r"\nUtilization: %.2f%%" % stat.utilization
        node.prefix_label += stat.prefix
        node.suffix_label += stat.suffix
        hw_tree.child.append(node)


def add_pipe_throttle_branch(stats, hw_tree):
    stats_list = list(stats.values())
    N = config.max_number_of_showed_nodes
    N = min(N, len(stats_list))
    stats_list_topN = sorted(stats_list, key=functools.cmp_to_key(cmp))[:N]
    while (stats_list_topN[N - 1].value < 50 and N > 2):
        N -= 1
    for stat in stats_list_topN[:N]:
        node = Node(stat.name)
        node.percentage = stat.value / 100
        node.prefix_label += stat.prefix
        node.suffix_label += stat.suffix
        hw_tree.child.append(node)


def add_lg_throttle_branch(stats, target_node):
    activewarps_per_activecycle = stats['activewarps_per_activecycle'].value
    if (activewarps_per_activecycle > config.low_activewarps_per_activecycle):
        node = Node("concurrent_warps")
        node.percentage = activewarps_per_activecycle
        node.show_percentage_or_value = SHOW_AS_RAW_VALUE
        target_node.child.append(node)


def add_sub_branch_for_longscoreboard_throughput(all_stats, bottleneck_unit, stats, target_node, current_percentage):
    if not target_node:
        return
    # @todo
    occupancy_limitation = {
        "SM": all_stats['block_limit_sm'].value,
        "Register": all_stats['block_limit_register'].value,
        # "Warps": all_stats['block_limit_warps'].value,
        "Shared Memory": all_stats['block_limit_shared_mem'].value
    }
    sorted_list = sorted(occupancy_limitation.items(), key=lambda x: x[1])
    limit_metrics = sorted_list[0][0]
    for i in range(1, len(sorted_list)):
        if sorted_list[i][1] == sorted_list[0][1]:
            limit_metrics += ", " + sorted_list[i][0]

    node = Node("occupancy")
    node.prefix_label = "Max active warps: %d\nTheoretical active warps: %.2f\nAchieved active warps: %.2f\nRegister usage per thread: %d\nBlocksize: %d\nLimited by: %s" % (
    config.max_avtive_warps_per_SM,
    all_stats["theoretical_active_warps"].value, all_stats["activewarps_per_activecycle"].value,
    all_stats["register_per_thread"].value, all_stats['launch_block_size'].value, limit_metrics)
    target_node.child.append(node)

    bottleneck_unit_latency_node = find_node(target_node, bottleneck_unit + "_latency")
    if not bottleneck_unit_latency_node:
        print("Couldn't find throughput bottlneck node for ", bottleneck_unit)
        return
    bottleneck_unit_latency_node.suffix_label += "\nutilized %.2f of elapased clocks" % stats['util_rate'].value
    del stats['util_rate']
    for stat_name in stats:
        node = Node(stat_name)
        if not (stat_name.endswith("rate") or stat_name.endswith('ratio')):
            node.show_percentage_or_value = SHOW_AS_RAW_VALUE
        node.percentage = stats[stat_name].value
        bottleneck_unit_latency_node.child.append(node)


def add_sub_branch_for_longscoreboard_latency(stats, target_node, all_stats, memory_metrics):
    if not target_node:
        return
    latency_node_top = Node("avg_latency")
    latency_node_top.type = LATENCY_NODE
    latency_node_top.suffix_label = r"Average load global latency: %i\n" % int(all_stats['lg_ld_latency'].value)
    latency_node_top.suffix_label += r"Average load generic latency: %i" % int(all_stats['generic_ld_latency'].value)
    target_node.child.append(latency_node_top)
    target_node = latency_node_top
    total_latency = stats["total_latency"].value
    for unit in ["l1", "tlb", "l2", "fb"]:
        full_name = unit + "_latency"
        stat = stats[full_name]
        node = Node(stat.name)
        node.type = LATENCY_NODE
        node.show_percentage_or_value = SHOW_AS_PERCENTAGE
        node.percentage = stat.value / total_latency
        target_node.child.append(node)
        target_node = node
        cycles = stats[unit + "_cycles"].value
        target_node.suffix_label = r" of average latency (weighted)"
        target_node.suffix_label += r"\navg cycles spent at this level: %i" % (int(cycles))
        if (unit not in memory_metrics.bottleneck):
            unit_stats = {}
            if (unit == "l1"):
                add_l1_stats(unit_stats, all_stats, memory_metrics)
            elif (unit == "tlb"):
                add_utlb_stats(unit_stats, all_stats, memory_metrics)
                add_l1tlb_stats(unit_stats, all_stats, memory_metrics)
            elif (unit == "l2"):
                add_l2_stats(unit_stats, all_stats, memory_metrics)
            elif (unit == "fb"):
                add_fb_stats(unit_stats, all_stats, memory_metrics)
            print(unit_stats)
            for key in unit_stats:
                stat = unit_stats[key]
                node = Node(stat.name)
                if ("rate" not in stat.name):
                    node.show_percentage_or_value = SHOW_AS_RAW_VALUE
                node.percentage = stat.value
                target_node.child.append(node)


def add_shared_memory_info(stats, shared_mem_stats, memory_metrics):
    shared_ld_requests = stats['shared_ld_requests']
    shared_ld_data_conflicts = stats['shared_ld_data_conflicts']
    if shared_ld_requests.value != 0:
        memory_metrics.shared_ld_conflict_per_request = shared_ld_data_conflicts.value / shared_ld_requests.value
    else:
        memory_metrics.shared_ld_conflict_per_request = 0

    shared_st_data_conflicts = stats['shared_st_data_conflicts']
    shared_st_requests = stats['shared_st_requests']
    if shared_st_requests.value != 0:
        memory_metrics.shared_st_conflict_per_request = shared_st_data_conflicts.value / shared_st_requests.value
    else:
        memory_metrics.shared_st_conflict_per_request = 0


def add_branch_for_mio_throttle(all_stats, shared_mem_stats, memory_metrics, target_node):
    if not target_node:
        return
    if memory_metrics.shared_ld_conflict_per_request is not None and memory_metrics.shared_ld_conflict_per_request > config.conflict_high_threshold:
        node = Node("mio_shared_ld_conflict")
        node.percentage = memory_metrics.shared_ld_conflict_per_request
        node.show_percentage_or_value = SHOW_AS_RAW_VALUE
        target_node.child.append(node)


def add_branch_for_short_scoreboard(all_stats, shared_mem_stats, memory_metrics, target_node):
    if not target_node:
        return
    if memory_metrics.shared_ld_conflict_per_request is not None and memory_metrics.shared_ld_conflict_per_request > config.conflict_high_threshold:
        node = Node("short_shared_ld_conflict")
        node.percentage = memory_metrics.shared_ld_conflict_per_request
        node.show_percentage_or_value = SHOW_AS_RAW_VALUE
        target_node.child.append(node)
    if memory_metrics.shared_st_conflict_per_request is not None and memory_metrics.shared_st_conflict_per_request > config.conflict_high_threshold:
        node = Node("short_shared_st_conflict")
        node.percentage = memory_metrics.shared_st_conflict_per_request
        node.show_percentage_or_value = SHOW_AS_RAW_VALUE
        target_node.child.append(node)


def find_node(hw_tree, node_name):
    if hw_tree is None:
        print("Error: You are trying to find %s in a none tree." % node_name)
    tmp_queue = [hw_tree]
    while tmp_queue:
        anode: Node = tmp_queue.pop(0)
        if anode.name == node_name:
            return anode
        tmp_queue += anode.child
    return None
