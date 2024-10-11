package com.smu.jkliu;

import com.smu.jkliu.core.Config;
import com.smu.jkliu.soothelper.CGExtractor;
import com.smu.jkliu.soothelper.Initializator;
import com.smu.jkliu.utils.FileProcessor;
import org.apache.commons.cli.*;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.File;
import java.util.HashSet;

public class Main {
    private static final Logger logger = LogManager.getLogger("Main");

    private static Options getOptions() {
        Options options = new Options();
        options.addOption("h", false, "-h: Show the help information.");

        options.addOption("apkPath", true, "-apkDir: Set the path to the apk under analysis.");
        options.addOption("resultDir", true, "-resultDir: Set the result directory.");
        options.addOption("androidJar", true, "-androidJar: Set the path of android.jar.");
        return options;
    }

    private static void analyzeArgs(CommandLine mCmd) {
        if (null == mCmd)
            System.exit(-1);

        if (mCmd.hasOption("h")) {
            HelpFormatter formatter = new HelpFormatter();
            formatter.setWidth(120);
            formatter.printHelp("java -jar [jarFile] [options] [-apkPath] [-resultDir] [-androidJar]\n" +
                    "E.g. -apkPath apk_path -resultDir result -androidJar platforms", getOptions());
            System.exit(0);
        }

        Config.androidJar = new File(mCmd.getOptionValue("androidJar", ""));
        Config.apkPath = mCmd.getOptionValue("apkPath", "");
        Config.resultDir = mCmd.getOptionValue("resultDir", "");
    }

    private static void extractingCG() {
        Initializator.initializeSoot(Config.apkPath);
        HashSet<String> CG = CGExtractor.extractCG();
//        HashSet<String> methods = CGExtractor.extractMethods();
        FileProcessor.write2File(Config.resultDir + "/cg.txt", CG);
//        FileProcessor.write2File(Config.resultDir + "/methods.txt", methods);
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
        extractingCG();
    }
}
