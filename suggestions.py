from gather import find_node
from data_struct import Node
from data_struct import config, SUGGESTION_NODE


def mio_throttle_short_scoreboard_common_suggest(stats, shared_mem_stats, memory_metrics, conflict_high_threshold):
    conflict_suggestion = []
    transaction_size_suggestion = []

    if memory_metrics.shared_ld_conflict_per_request is not None and memory_metrics.shared_ld_conflict_per_request > conflict_high_threshold:
        conflict_suggestion.append(('load', memory_metrics.shared_ld_conflict_per_request))
        shared_ld_32b = shared_mem_stats.get('shared_ld_32b_executed')
        shared_ld_64b = shared_mem_stats.get('shared_ld_64b_executed')
        shared_ld = shared_mem_stats.get('shared_ld_executed')
        if shared_ld_32b and shared_ld_64b and shared_ld and shared_ld.value != 0 and (((
                                                                                                shared_ld_32b.value + shared_ld_64b.value) / shared_ld.value > 0.66) or shared_ld_32b.value / shared_ld.value > 0.33 or shared_ld_64b.value / shared_ld.value > 0.33):
            transaction_size_suggestion.append('load')

    if memory_metrics.shared_st_conflict_per_request != 0 and memory_metrics.shared_st_conflict_per_request > conflict_high_threshold:
        conflict_suggestion.append(('store', memory_metrics.shared_st_conflict_per_request))
        shared_st_32b = shared_mem_stats.get('shared_st_32b_executed')
        shared_st_64b = shared_mem_stats.get('shared_st_64b_executed')
        shared_st = shared_mem_stats.get('shared_st_executed')
        if shared_st_32b and shared_st_64b and shared_st and shared_st.value != 0 and (((
                                                                                                shared_st_32b.value + shared_st_64b.value) / shared_st.value > 0.66) or shared_st_32b.value / shared_st.value > 0.33 or shared_st_64b.value / shared_st.value > 0.33):
            transaction_size_suggestion.append('store')
    return conflict_suggestion, transaction_size_suggestion


def mio_throttle_suggest(hw_tree, stats, shared_mem_stats):
    mio_node = find_node(hw_tree, "warp_cant_issue_mio_throttle")
    if not mio_node:
        return
    tmp_suggestion = r"This happens when shared memory loads can't be issued due to backpressure. Try code restructuring to reduce the number of concurrent shared memory loads, e.g. by issuing wider loads, spreading the loads, reducing the unrolling in the kernel"
    if config.compute_capability >= 80:
        tmp_suggestion += r", or change to asynchronous shared memory copy."
    else:
        tmp_suggestion += '.'
    add_suggestion(mio_node, tmp_suggestion)
    conflict_node = find_node(mio_node, "mio_shared_ld_conflict")
    if conflict_node:
        add_suggestion(conflict_node,
                       r"Fewer data conflicts can reduce the time for loads, and can help alleviate the throttle cycles.")


def short_scoreboard_suggest(hw_tree, stats, shared_mem_stats):
    short_scoreboard_node = find_node(hw_tree, "warp_cant_issue_short_scoreboard")
    if not short_scoreboard_node:
        return
    conflict_node = find_node(short_scoreboard_node, "short_shared_ld_conflict")
    if conflict_node:
        add_suggestion(conflict_node,
                       r"Fewer data conflicts can reduce the time for loads")
    conflict_node = find_node(short_scoreboard_node, "short_shared_st_conflict")
    if conflict_node:
        add_suggestion(conflict_node,
                       r"Fewer store data conflicts can help make shared memory access more efficient")
    if config.compute_capability >= 80:
        add_suggestion(short_scoreboard_node, "Try to use asynchronous shared memory copy.")

    common_more_warps_suggestion(short_scoreboard_node, stats, hw_tree,
                                 "More warps may help hide the shared memory latency.")
    add_suggestion(short_scoreboard_node, r"Consider loop unrolling to hide shared memory and MIO latency.")


def pipe_suggest(hw_tree, stats):
    pipe_node = find_node(hw_tree, "warp_cant_issue_pipe_throttle")
    if not pipe_node:
        return
    fp64_node = find_node(hw_tree, "pipe_fp64")
    if fp64_node:
        tensor_node = find_node(hw_tree, "pipe_tensor_fp64")
        if not tensor_node:
            add_suggestion(fp64_node,
                           r"Tensor cores can double the rate of FP64 ops in some cases. Investigate if your application can exploit them.")


def barrier_suggest(hw_tree, stats):
    barrier_node = find_node(hw_tree, "warp_cant_issue_barrier")
    if not barrier_node:
        return
    threads_per_block = stats['launch_block_size'].value
    if threads_per_block > config.warp_size:
        add_suggestion(barrier_node,
                       r"The number of threads per block is about %d, but only %d needed for a warp. Splitting them into multiple CTAs may help reduce barrier cycles (but may affect intra-CTA sharing via shared memory)." % (
                       int(threads_per_block),
                       config.warp_size))
    else:
        common_more_warps_suggestion(barrier_node, stats, hw_tree,
                                     "More concurrent warps may help reduce cycles wasted due to barriers.")
    if config.compute_capability >= 80:
        add_suggestion(barrier_node, r"Try to use asynchronous barrier.")

    #     @todo need fix. The newest version(2021.1.0) of ncu has changed this counter.
    if stats.get("not_predicated_off_thread_per_inst_executed", None):
        not_predicated_off_thread_per_inst_executed = stats["not_predicated_off_thread_per_inst_executed"]
    elif stats.get("not_predicated_off_thread_per_inst_executed2", None):
        not_predicated_off_thread_per_inst_executed = stats["not_predicated_off_thread_per_inst_executed2"]
    else:
        return
    if not_predicated_off_thread_per_inst_executed.value < 17:
        add_suggestion(barrier_node,
                       r"High thread divergence: %d%% threads in a warp execute together. Reducing divergence may help reduce barrier cycles." % (
                               not_predicated_off_thread_per_inst_executed.value / config.warp_size * 100))


def membar_suggest(hw_tree, stats):
    membar_node = find_node(hw_tree, "warp_cant_issue_membar")
    if not membar_node:
        return
    add_suggestion(membar_node, r"Try to reduce the scope of the memory barrier to warp or thread block")


def branch_solving_suggest(hw_tree, stats):
    branch_solving_node = find_node(hw_tree, "warp_cant_issue_branch_resolving")
    if not branch_solving_node:
        return
    not_predicated_off_thread_per_inst_executed = stats["not_predicated_off_thread_per_inst_executed"]
    if not_predicated_off_thread_per_inst_executed.value < config.high_not_predicated_off_thread_per_inst_executed:
        add_suggestion(branch_solving_node,
                       r"High thread divergence: %d %% threads in a warp execute together. Reducing divergence may help reduce the branch resolving cycles." % (
                               not_predicated_off_thread_per_inst_executed.value / config.max_not_predicated_off_thread_per_inst_executed * 100))


def drain_suggest(hw_tree, stats):
    drain_node = find_node(hw_tree, "warp_cant_issue_drain")
    if not drain_node:
        return
    add_suggestion(drain_node,
                   r"Try to move the burst of global memory stores away from the kernel end to earlier in the execution.")
    common_more_warps_suggestion(drain_node, stats, hw_tree,
                                 "More warps may help utilize the cycles wasted due to pending stores.")


def imc_miss_suggest(hw_tree, stats):
    imc_miss_node = find_node(hw_tree, "warp_cant_issue_imc_miss")
    if not imc_miss_node:
        return
    imc_hit_rate_stat = stats['imc_hitrate']
    imc_miss_rate = None
    if imc_hit_rate_stat:
        imc_miss_rate = (100 - imc_hit_rate_stat.value) / 100
    suggestion = ''
    if imc_miss_rate != None:
        suggestion += r"imc miss rate: %.2f\n" % imc_miss_rate
    suggestion += r"Might be better to use non-constants."
    add_suggestion(imc_miss_node, suggestion)


def dispatch_stall_suggest(hw_tree, stats):
    dispatch_stall_node = find_node(hw_tree, "warp_cant_issue_dispatch_stall")
    if not dispatch_stall_node:
        return
    # add_suggestion(dispatch_stall_node, r"Could be due to limited register read bandwidth.")


def lg_credit_throttle_suggest(hw_tree, stats):
    lg_credit_throttle_node = find_node(hw_tree, "warp_cant_issue_lg_credit_throttle")
    if not lg_credit_throttle_node:
        return
    add_suggestion(lg_credit_throttle_node,
                   r"This happens when global memory loads can't be issued due to backpressure. Try code restructuring to reduce the number of concurrent global loads, e.g. by issuing wider loads, spreading the loads, or reducing the unrolling in the kernel.")
    active_warps_node = find_node(hw_tree, "concurrent_warps")
    if active_warps_node:
        add_suggestion(lg_credit_throttle_node,
                       r"Reducing concurrent warps may help.")


def memory_suggest(hw_tree, stats, bottleneck_unit, memory_metrics):
    occupancy_node = find_node(hw_tree, "occupancy")
    activewarps_per_activecycle = stats['activewarps_per_activecycle'].value
    if activewarps_per_activecycle < config.low_activewarps_per_activecycle:
        add_suggestion(occupancy_node, "Try to increase active warps by reducing register usage or block size")

    elapsedClocks = stats['elapsedClocks'].value
    high_l1_lines_per_instruction = config.warp_size * memory_metrics.bpl1 / config.BYTES_PER_L1_INSTRUCTION

    l1_node = find_node(hw_tree, "throughput_l1")
    if not l1_node:
        l1_node = find_node(hw_tree, "l1_latency")
    if not l1_node:
        print("Can't find throughput or latency node for L1")
    else:
        # Case 1: the l1 throughput is close to peak number
        l1_throughput = memory_metrics.throughputs['l1']
        if l1_throughput / elapsedClocks >= config.high_l1_throughput:
            add_suggestion(l1_node, "Your L1 read bandwidth is close to peak. ")
            add_suggestion(l1_node, r"Try to reduce L1 utilization, e.g. by using temporary variables.")
            activewarps_per_activecycle = stats['activewarps_per_activecycle'].value
            if activewarps_per_activecycle is not None and activewarps_per_activecycle < config.low_activewarps_per_activecycle and not find_node(
                    hw_tree, "warp_cant_issue_mio_throttle"):
                add_suggestion(l1_node,
                               r"Current number of active warps per active cycle is %.2f(the max allowed is 64). Try to issue more warps to hide L1 latency." % (
                                   activewarps_per_activecycle))
        else:
            # Case 2: The l1 throughput is not close to peak number
            if memory_metrics.l1_hit_rate > config.high_l1_hit_rate:
                if memory_metrics.l1_conflict_rate is not None and memory_metrics.l1_conflict_rate > config.high_l1_conflict_rate:
                    l1_conflict_rate_node = find_node(hw_tree, "l1_conflict_rate")
                    if l1_conflict_rate_node:
                        add_suggestion(l1_conflict_rate_node,
                                       r"Try to rearrange your data accesses to reduce L1 data conflicts.")
                    if memory_metrics.l1_lines_per_instruction is not None and memory_metrics.l1_lines_per_instruction > high_l1_lines_per_instruction:
                        l1_lines_per_instruction_node = find_node(hw_tree, "l1_lines_per_instruction")
                        if l1_lines_per_instruction_node:
                            add_suggestion(l1_lines_per_instruction_node,
                                           r"Try to rearrange your data access strides to read fewer L1 cache lines per load.")

    # only complain about utlb if throughput bound on it
    if bottleneck_unit == 'utlb':
        utlb_node = find_node(hw_tree, "throughput_utlb")
        if not utlb_node:
            return
            if memory_metrics.l1_hit_rate < config.low_l1_hit_rate:
                add_suggestion(utlb_node,
                               r"Try to reduce the L1 miss rate to reduce utilization of uTLB.")
            if memory_metrics.l1_lines_per_instruction and memory_metrics.l1_lines_per_instruction > high_l1_lines_per_instruction:
                add_suggestion(utlb_node,
                               r"Try to rearrange your data access strides to read fewer uTLB entries per load.")

    l1tlb_node = find_node(hw_tree, "throughput_l1tlb")
    if (not l1tlb_node):
        l1tlb_node = find_node(hw_tree, "latency_tlb")
    if not l1tlb_node:
        print("Can't find throughput or latency node for L1TLB")
    else:
        l1_miss_rate_node = find_node(l1tlb_node, "l1_miss_rate")
        if l1_miss_rate_node:
            common_l1_miss_rate_suggestion(l1_miss_rate_node, memory_metrics)
        else:
            common_l1_miss_rate_suggestion(l1tlb_node, memory_metrics)
        if memory_metrics.utlb_miss_rate is not None and memory_metrics.utlb_miss_rate >= config.high_utlb_miss_rate:
            utlb_miss_rate = find_node(l1tlb_node, "utlb_miss_rate")
            if utlb_miss_rate:
                add_suggestion(utlb_miss_rate,
                               r"Try to rearrange your data accesses for SMs to stay within uTLB pages, e.g. by tiling.")
        # only complain if throughput bound
        if bottleneck_unit == "l1tlb":
            if memory_metrics.l1_lines_per_instruction and memory_metrics.l1_lines_per_instruction > high_l1_lines_per_instruction:
                l1_lines_per_load_node = find_node(hw_tree, "l1_lines_per_instruction")
                if l1_lines_per_load_node:
                    add_suggestion(l1_lines_per_load_node,
                                   r"Try to reduce your data access strides to read fewer TLB entries per load.")

    l2_node = find_node(hw_tree, "throughput_l2")
    if not l2_node:
        l2_node = find_node(hw_tree, "l2_latency")
    if not l2_node:
        print("Can't find throughput or latency node for L2")
    else:
        # across_load_coalescing_ratio
        if memory_metrics.l2_bank_conflict_rate is not None and memory_metrics.l2_bank_conflict_rate > config.high_l2_bank_conflict_rate:
            l2_bank_conflict_rate_node = find_node(l2_node, "l2_bank_conflict_rate")
            if (l2_bank_conflict_rate_node):
                add_suggestion(l2_bank_conflict_rate_node,
                               r"Try to rearrange your data accesses to reduce bank conflicts.")
        if memory_metrics.l2_miss_rate is not None and memory_metrics.l2_miss_rate >= config.high_l2_miss_rate:
            # @todo this part is not clear
            fb_node = find_node(hw_tree, "throughput_fb")
            if not fb_node:
                fb_node = find_node(hw_tree, "fb_latency")
            if not fb_node:
                print("Can't find throughput or latency node for FB")
            else:
                l2_miss_node = find_node(fb_node, "l2_miss_rate")
                if l2_miss_node:
                    pass
                    # add_suggestion(l2_miss_node,
                    #             r"Try to reduce the L2 miss rate to reduce utilization of FB, e.g. by L2 persisting access policy")

    fb_node = find_node(hw_tree, "throughput_fb")
    if not fb_node:
        fb_node = find_node(hw_tree, "fb_latency")
    if not fb_node:
        print("Can't find throughput or latency node for FB")
    else:
        if memory_metrics.l2_miss_rate is not None and memory_metrics.l2_miss_rate >= config.high_l2_miss_rate:
            l2_miss_node = find_node(fb_node, "l2_miss_rate")
            if l2_miss_node:
                pass
                # add_suggestion(l2_miss_node,
                #             r"Try to reduce the L2 miss rate to reduce utilization of FB, e.g. by L2 persisting access policy")
        if memory_metrics.access_per_activate is not None and memory_metrics.access_per_activate < config.low_access_per_activate:
            access_per_activate_node = find_node(fb_node, "access_per_activate")
            if access_per_activate_node:
                add_suggestion(access_per_activate_node,
                               r"Try to rearrange the data accesses to limit activating pages, e.g. by increasing spatial locality.")
        if memory_metrics.average_dram_banks is not None and memory_metrics.average_dram_banks < config.low_bank_per_access:
            bank_per_access_node = find_node(fb_node, "average_dram_banks")
            if (bank_per_access_node):
                suggestion = r"Bank utilization is low, typically happens when not enough concurrent requests."

                activewarps_per_activecycle = stats['activewarps_per_activecycle'].value
                if activewarps_per_activecycle is not None and activewarps_per_activecycle < config.low_activewarps_per_activecycle and not find_node(
                        hw_tree, "warp_cant_issue_mio_throttle"):
                    suggestion += " Current number of active warps per active cycle is %.2f (max allowed is 64). If possible, you may be able to hide memory latency by running more concurrent warps." % (
                        activewarps_per_activecycle)
                add_suggestion(bank_per_access_node, suggestion)
        if memory_metrics.compress_rate is not None:
            compress_node = find_node(fb_node, "compression_success_rate")
            if (compress_node):
                if memory_metrics.compress_rate == 0:
                    add_suggestion(compress_node, r"Try enabling compression to reduce FB utilization.")
                elif memory_metrics.compress_rate <= config.low_compress_rate:
                    add_suggestion(compress_node,
                                   r"Compression rate is low; try enabling compression on more data if possible")
        dram_noreq_node = find_node(fb_node, "dram_noReq")
        if dram_noreq_node:
            add_suggestion(dram_noreq_node,
                           r"DRAM not used at times due to absence of requests.  If possible, spread out reads to global memory to avoid DRAM inactivity and/or bursts. You may also be able to reduce idle cycles by prefetching data.")


def wait_suggestion(hw_tree, stats):
    wait_node = find_node(hw_tree, "warp_cant_issue_wait")
    if not wait_node:
        return
    add_suggestion(wait_node,
                   r"Long-latency instructions consuming each other's results spaced too close together. Try to restructure or unroll to increase spacing.")


def common_l1_miss_rate_suggestion(target_node, memory_metrics):
    if memory_metrics.l1_hit_rate < config.low_l1_hit_rate:
        add_suggestion(target_node,
                       r"Try to reduce the L1 miss rate to reduce utilization of the rest of memory heirarchy. You may be able to increase L1 size by reducing the shared memory size.")


def common_more_warps_suggestion(target_node, stats, hw_tree, suffix):
    activewarps_per_activecycle = stats['activewarps_per_activecycle'].value
    if activewarps_per_activecycle < config.low_activewarps_per_activecycle and not find_node(
            hw_tree, "warp_cant_issue_mio_throttle"):
        add_suggestion(target_node,
                       #   @todo  64?? in ncu, this number is 32.
                       r"Current number of active warps per active cycle is %.2f (max allowed is 64). " % (
                           activewarps_per_activecycle) + suffix)


def add_suggestion(target_node: Node, content, prefix=''):
    if not target_node:
        print("Failed to add suggestion:", content)
        return
    s_node = Node("suggestion_for_%s_%d" % (target_node.name, len(target_node.child)))
    s_node.type = SUGGESTION_NODE
    s_node.suffix_label = content
    s_node.prefix_label = prefix
    target_node.child.append(s_node)
