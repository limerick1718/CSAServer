package com.smu.jkliu.soothelper;

import com.smu.jkliu.core.Config;

import soot.*;
import soot.jimple.toolkits.callgraph.CallGraphBuilder;
import soot.options.Options;

import java.util.Collections;

public class Initializator {

    private static String androidJAR = Config.androidJar.getAbsolutePath();


    public static void initializeSoot(String apk) {

        G.reset();
        Options.v().debug();
        Options.v().set_allow_phantom_refs(true);
        Options.v().set_whole_program(true);
        Options.v().set_prepend_classpath(true);
        Options.v().set_src_prec(Options.src_prec_apk);
        Options.v().set_process_multiple_dex(true);
        Options.v().set_include_all(true);

        Options.v().set_process_dir(Collections.singletonList(apk));
        Options.v().set_android_jars(androidJAR);

        Scene.v().loadNecessaryClasses();

//        build cg
        CallGraphBuilder callGraphBuilder = new CallGraphBuilder();
        callGraphBuilder.build();
    }
}
