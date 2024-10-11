package com.smu.jkliu.core;

import java.io.File;

public class Config {

    public static String apkPath;
    public static File androidJar;
    public static String packageName;
    public static String resultDir;

    private static class SingletonInstance {
        private static final Config INSTANCE = new Config();
    }

    public static Config getInstance() {
        return SingletonInstance.INSTANCE;
    }

}
