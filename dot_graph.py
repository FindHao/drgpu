from graphviz import Digraph
from data_struct import node_name_map_counter, NORMAL_TREE_NODE, \
SUGGESTION_NODE, SHOW_AS_PERCENTAGE, SOURCE_CODE_NODE, LATENCY_NODE, \
    Node, MEMORY_LATENCY_HIERARCHY
import re

colors = [
    "ivory", "aquamarine", "red", "chartreuse", "khaki", "hotpink", "dodgerblue", "gainsboro", "skyblue", "wheat",
    "thistle",
]


def break_to_multiple_lines(inp, char_per_line):
    out = ""
    splits = re.split(r"\s", inp)
    cur_line = ""
    for next_word in splits:
        if len(next_word) >= char_per_line:
            if cur_line != "":
                out += cur_line + "\n" + next_word + "\n"
            else:
                out += next_word + "\n"
            cur_line = ""
        elif len(cur_line) + len(next_word) < char_per_line:
            cur_line += " " + next_word
        else:
            out += cur_line + "\n"
            cur_line = next_word
    if cur_line != "":
        out += cur_line
    return out


def build_dot_graph(hw_tree, dot_file_name):
    g = Digraph('hw tree')
    # [(father.name, child), ], have to record their father
    theq = [(hw_tree.name, hw_tree)]
    color_i = 0

    pattern_name = [r"inst_executed_(.*)_ops", r"cant_dispatch_(.*)"]

    while theq:

        apair = theq.pop(0)
        cur_child: Node = apair[1]
        father_name = apair[0]
        node_shape = 'box'
        if cur_child.type == SUGGESTION_NODE:
            tmp_nodename = "Suggestion"
            tmp_color = 'mediumseagreen'
        elif cur_child.type == SOURCE_CODE_NODE:
            tmp_nodename = 'Source Code'
            tmp_color = 'bisque'
        else:
            tmp_nodename = node_name_map_counter.get(cur_child.name)
            if not tmp_nodename:
                for pattern in pattern_name:
                    reg = re.compile(pattern)
                    result = reg.findall(cur_child.name)
                    if result:
                        tmp_nodename = result[0]
                        break
            if not tmp_nodename:
                tmp_nodename = cur_child.name
            if cur_child.type == LATENCY_NODE:
                tmp_color = 'lightsalmon'
            else:
                tmp_color = 'lightgrey'

        if cur_child.name == 'root':
            alabel = cur_child.name
        else:
            if cur_child.type == NORMAL_TREE_NODE or cur_child.type == LATENCY_NODE:
                if cur_child.percentage is None:
                    tmpstr = ''
                else:
                    if cur_child.show_percentage_or_value == SHOW_AS_PERCENTAGE:
                        tmpstr = r"{:.2%}".format(cur_child.percentage)
                    else:
                        if isinstance(cur_child.percentage, float):
                            tmpstr = r"{:.2f}".format(cur_child.percentage)
                        else:
                            tmpstr = cur_child.percentage
                alabel = r"%s\n" % (break_to_multiple_lines(tmp_nodename, 25))
                if cur_child.prefix_label:
                    alabel += r'%s' % cur_child.prefix_label
                alabel += r"%s" % str(tmpstr)
                if cur_child.suffix_label:
                    alabel += r"%s" % cur_child.suffix_label
            # suggestion node
            elif cur_child.type == SUGGESTION_NODE:
                # alabel = r"%s\n%s" % (tmp_nodename, break_to_multiple_lines(cur_child.suffix_label, 25))
                alabel = r"%s" % (break_to_multiple_lines(cur_child.suffix_label, 25))
            elif cur_child.type == SOURCE_CODE_NODE:
                alabel = r"%s" % cur_child.suffix_label
            else:
                print("No such type of node", cur_child.type)

        # g.node(name=cur_child.name, label=alabel, style="filled", color=colors[color_i % len(colors)])
        # g.node(name=cur_child.name, label=alabel, style="filled", color="/ylgn9/%d" % (9 - color_i%9))
        g.node(name=cur_child.name, label=alabel, style="filled", color=tmp_color, shape=node_shape)
        color_i += 1
        if father_name != cur_child.name:
            if (father_name, cur_child.name) in MEMORY_LATENCY_HIERARCHY:
                if father_name == 'avg_latency':
                    alabel = '='
                else:
                    alabel  = '+'
                edge_color = 'firebrick'
            else:
                edge_color = 'black'
                alabel = ''
            g.edge(father_name, cur_child.name, color=edge_color, label=alabel)
        for next_child in cur_child.child:
            theq.append((cur_child.name, next_child))
    g.format = 'svg'
    g.render(dot_file_name, view=False)
