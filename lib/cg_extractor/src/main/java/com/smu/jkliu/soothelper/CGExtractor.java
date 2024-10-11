package com.smu.jkliu.soothelper;

import soot.Scene;
import soot.SootClass;
import soot.SootMethod;
import soot.jimple.toolkits.callgraph.CallGraph;
import soot.jimple.toolkits.callgraph.Edge;
import soot.util.Chain;

import java.util.HashSet;
import java.util.List;

public class CGExtractor {

    public static HashSet<String> extractCG() {
        HashSet<String> edges = new HashSet<>();
        CallGraph callGraph = Scene.v().getCallGraph();
        for (Edge edge : callGraph) {
            String src = edge.getSrc().toString();
            String tgt = edge.getTgt().toString();
            String currentEdge = src + " -> " + tgt;
            edges.add(currentEdge);
        }
        return edges;
    }

    public static HashSet<String> extractMethods() {
        HashSet<String> methods = new HashSet<>();
        Chain<SootClass> classes = Scene.v().getClasses();
        for (SootClass sootClass : classes) {
            List<SootMethod> classMethods = sootClass.getMethods();
            for (SootMethod method : classMethods) {
                methods.add(method.toString());
            }
        }
        return methods;
    }

}
