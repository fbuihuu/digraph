#! /usr/bin/env python
import sys, __builtin__

__all__ = ["DirectedGraph", "transpose", "condensate", "dot", "open"]

# Directed graph built out of sets and dictionaries.
class DirectedGraph(object):
    def __init__(self, name):
        self.name = name
        self.vertices = {}

    def __str__(self):
        return self.name

    def __len__(self):
        return len(self.vertices)

    def __iter__(self):
        return iter(self.vertices.keys())

    def __getitem__(self, node):
        return self.vertices[node]

    def nodes(self):
        return self.vertices.keys()

    def iteritems(self):
        for k in self:
            yield (k, self[k])

    def add_node(self, node):
        if node not in self.vertices:
            self.vertices[node] = set()

    def add_arc(self, n1, n2):
        if n1 not in self.vertices:
            self.vertices[n1] = set()
        if n2 not in self.vertices:
            self.vertices[n2] = set()
        self.vertices[n1].add(n2)

    # Depth First Search - Postordering Traversing.
    # If the directed graph is acyclic then it traverses
    # the nodes in a reversed topological order.
    def topological_iter(self, root=None, reverse=False):
        visited = set()
        sorted  = []

        def __depth_first_traverse(node):
            visited.add(node)
            for next in self.vertices[node]:
                if next not in visited:
                    __depth_first_traverse(next)
            sorted.append(node)

        vertices = self.vertices
        if root is not None:
            vertices = [root]

        for node in vertices:
            if node not in visited:
                __depth_first_traverse(node)

        if reverse:
            sorted.reverse()
        return iter(sorted)

def transpose(graph):
    transposed = DirectedGraph("Transpose of %s" % str(graph))
    for node in graph:
        transposed.add_node(node)
        for next in graph[node]:
            transposed.add_arc(next, node)
    return transposed

# Build the condensation of the graph
def condensate(graph):
    visited = set()

    # Compute the strongly connected components list of a directed
    # graph using Kosaraju's algorithm.
    groups = []
    for leader in graph.topological_iter(reverse=True):
        if leader not in visited:
            group = set([leader])
            for node in transpose(graph).topological_iter(root=leader):
                if node not in visited:
                    if node != leader:
                        group.add(node)
                    visited.add(node)
            groups.append((leader, group))

    # compute the reverse mapping to easily know which subgraph a node
    # belongs to. The subgraphs contain only nodes but no vertexes at
    # all. They're added after.
    mapping = {}
    for leader, group in groups:
        if len(group) > 1:
            percent = 100 * len(group) / len(graph)
            group_name = "Group(%s - %d[%d%%])" % (leader, len(group), percent)
            leader = DirectedGraph(group_name)
        for node in group:
            mapping[node] = leader

    condensation = DirectedGraph("Condensation of %s" % str(graph))
    for group in zip(*groups)[1]:
        for node in group:
            # mapping[node] might not be linked to any other nodes.
            condensation.add_node(mapping[node])
            for next in graph[node]:
                if next in group and isinstance(mapping[node], DirectedGraph):
                    mapping[node].add_arc(node, next)
                else:
                    condensation.add_arc(mapping[node], mapping[next])

    return condensation

def __dot(graph, stream, expand, concentrate):
    clusters = {}

    print >>stream, 'digraph "%s" {' % str(graph)
    print >>stream, '  compound=%s;' % ("true" if expand else "false")
    print >>stream, '  concentrate=%s;' % ("true" if concentrate else "false")
    for node in graph:
        if isinstance(node, DirectedGraph) and expand:
            subgraph = node
            name = 'cluster%d' % len(clusters)
            print >>stream, '  subgraph %s {' % name
            print >>stream, '    label="%s" ' % str(subgraph)
            for subnode in subgraph:
                for subnext in subgraph[subnode]:
                    print >>stream, '    "%s" -> "%s";' % (subnode, subnext)
            print >>stream, '  }'
            # pickup a random node inside the cluster so we can use it
            # later to draw arcs to/from this cluster.
            clusters[subgraph] = (name, subnext)
        else:
            clusters[node] = (None, node)

    for src in graph:
        src_cluster, src_node = clusters[src]
        if len(graph[src]) == 0:
            print >>stream, '  "%s";' % src_node
        for dst in graph[src]:
            dst_cluster, dst_node = clusters[dst]
            if src_cluster is not None and dst_cluster is not None:
                trailer = ' [ltail=%s,lhead=%s]' % (src_cluster, dst_cluster)
            elif src_cluster is not None:
                trailer = ' [ltail=%s]' % src_cluster
            elif dst_cluster is not None:
                trailer = ' [lhead=%s]' % dst_cluster
            else:
                trailer = ''
            print >>stream, '  "%s" -> "%s"' % (src_node, dst_node) + trailer + ';'
    print >>stream, '}'

def dot(graph, filename=None, expand=False, concentrate=False):
    if filename is None:
        __dot(graph, None, expand, concentrate)
    else:
        with __builtin__.open(filename, 'w') as stream:
            __dot(graph, stream, expand, concentrate)

def open(filename, name=None):

    if name is None:
        import os
        name = os.path.basename(filename)

    with __builtin__.open(filename, 'r') as file:
        digraph = DirectedGraph(name)
        lineno = 0
        for line in file:
            if not line:
                break
            lineno = lineno + 1
            line = line.strip()
            # comments or blank lines
            if line == '' or line[0] in '#':
                continue
            words = line.split()
            # A single wors means add a single node to the graph.
            # Additional vertices from this node can be added later.
            if len(words) == 1:
                digraph.add_node(line)
            elif len(words) == 3:
                # for now only '->' sign is known
                if words[1] == "->":
                    digraph.add_arc(words[0], words[2])
                else:
                    raise ValueError("Illegal symbol at line %d\n" % lineno)
            else:
                raise ValueError("Incorrect syntax at line %d\n" % lineno)

    return digraph


def main(argc, argv):

    if argc != 2:
        sys.stderr.write("Usage: digraph.py <file>\n")
        exit(1)

    digraph = open(argv[1])

    #import pdb; pdb.set_trace()
    #dot(digraph)
    #exit()

    condensation = condensate(digraph)
    #dot(condensation)
    #exit()

    #print "Condensation vertices:"
    #print "---------------------"
    #for k,v in condensation.iteritems():
    #    print "%s : %s" % (k, map(str, v))

    print "Connected components:"
    print "--------------------"
    for node in condensation.nodes():
        if isinstance(node, DirectedGraph):
            nodes = node.nodes()
            if len(nodes) > 10:
                nodes = nodes[:10] + ["..."]
            print "* %s: %s" % (node, ', '.join(nodes))
            #dot(node)

    #print "Topological order:"
    #print "-----------------"
    #print ' -> '.join(map(str, condensation.topological_iter()))

    return 0


if __name__ == "__main__":
    sys.exit(main(len(sys.argv), sys.argv))
