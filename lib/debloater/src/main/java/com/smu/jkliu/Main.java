package com.smu.jkliu;

import java.io.File;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.apache.commons.cli.*;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import com.smu.jkliu.core.Config;
import com.smu.jkliu.instrument.Instrumentor;
import com.smu.jkliu.instrument.MethodTransformer;
import com.smu.jkliu.utils.FileProcessor;

import soot.BodyTransformer;

public class Main {
    private static final Logger logger = LogManager.getLogger("Main");

    private static Options getOptions() {
        Options options = new Options();
        options.addOption("h", false, "-h: Show the help information.");

        options.addOption("apkPath", true, "-apkDir: Set the path to the apk under analysis.");
        options.addOption("toDebloatPath", true, "-toDebloatPath: Set the path the file that contains to removed methods.");
        options.addOption("androidJar", true, "-androidJar: Set the path of android.jar.");
        return options;
    }

    private static void analyzeArgs(CommandLine mCmd) {
        if (null == mCmd)
            System.exit(-1);

        if (mCmd.hasOption("h")) {
            HelpFormatter formatter = new HelpFormatter();
            formatter.setWidth(120);
            formatter.printHelp("java -jar [jarFile] [options] [-path] [-name] [-outDir] [-toDebloatPath]\n" +
                    "E.g., -path apk\\ -name test.apk -outputDir result -client MainClient", getOptions());
            System.exit(0);
        }

        Config.androidJar = new File(mCmd.getOptionValue("androidJar", ""));
        Config.apkPath = mCmd.getOptionValue("apkPath", "");
        Config.toDebloatPath = mCmd.getOptionValue("toDebloatPath", "");
    }

    private static void debloating(String appName, String toDebloatPath) {
        String packageName = Config.packageName;
        HashSet<String> toDebloatMethodsStrings = new HashSet<>(FileProcessor.readFile(toDebloatPath));
        String apkPath = Config.apkPath;
        String debloatedDirPath = new File(Config.toDebloatPath).getParentFile().getAbsolutePath();
        new File(debloatedDirPath).mkdirs();
        long startTime = System.currentTimeMillis();
        System.out.println("APK path: " + apkPath);
        Instrumentor.initializeSoot(debloatedDirPath, apkPath);
        System.out.println("Initialized soot");
        List<BodyTransformer> transformers = new ArrayList<>();
        MethodTransformer e = new MethodTransformer(packageName, toDebloatMethodsStrings);
        transformers.add(e);
        Instrumentor.instrument(transformers, apkPath);
        System.out.println(debloatedDirPath + appName);
        Set<String> removedCounter = e.getRemovedCounter();
        Set<String> totalCounter = e.getTotalCounter();
        System.out.println("Removed " + removedCounter + " elements.");
        logger.info("Debloating finished.");
        long endTime = System.currentTimeMillis();
        System.out.println("Debloating time: " + (endTime - startTime) + "ms");
        FileProcessor.write2File(toDebloatPath.replace("config.csv", "removed_methods.csv"),removedCounter);
        FileProcessor.write2File(toDebloatPath.replace("config.csv", "total_methods.csv"),totalCounter);
        FileProcessor.write2File(toDebloatPath.replace("config.csv", "time.txt"),(endTime - startTime));
    }

    public static void main(String[] args) {
        logger.debug("Begin");
        CommandLineParser parser = new DefaultParser();
        try {
            CommandLine parseCMD = parser.parse(getOptions(), args, false);
            analyzeArgs(parseCMD);
        } catch (ParseException e) {
            e.printStackTrace();
        }
        debloating(Config.apkPath, Config.toDebloatPath);
    }
}
