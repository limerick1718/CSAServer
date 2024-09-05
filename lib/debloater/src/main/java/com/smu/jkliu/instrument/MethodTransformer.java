package com.smu.jkliu.instrument;

import soot.*;
import soot.jimple.*;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class MethodTransformer extends BodyTransformer {
    FastHierarchy fastHierarchy = Scene.v().getOrMakeFastHierarchy();
    Set<String> toRemoveMethods;
    static Set<String> removedCounter = new HashSet<>();
    static Set<String> totalCounter = new HashSet<>();
    String packageName;

    public MethodTransformer(String packageName, Set<String> toRemoveMethods) {
        this.toRemoveMethods = toRemoveMethods;
        System.out.println("Number of to debloate methods: " + toRemoveMethods.size());
        this.packageName = packageName;
    }

    @Override
    protected void internalTransform(Body body, String arg0, @SuppressWarnings("rawtypes") Map arg1) {
        SootMethod method = body.getMethod();
        String methodSignature = method.getSignature();
        totalCounter.add(methodSignature);
        if (toRemoveMethods.contains(methodSignature)) {
            JimpleBody jimpleBody = (JimpleBody) body;
            UnitPatchingChain units = jimpleBody.getUnits();
            removedCounter.add(methodSignature);
            HashSet<Stmt> toRemoveStmts = new HashSet<>();
            for (Unit unit : units) {
                if (unit instanceof Stmt) {
                    Stmt stmt = (Stmt) unit;
                    if (stmt instanceof IdentityStmt) {
                        continue;
                    }
                    if (stmt instanceof ReturnVoidStmt) {
                        continue;
                    }
                    if (stmt instanceof ReturnStmt) {
                        ReturnStmt returnStmt = (ReturnStmt) stmt;
                        Value v = NullConstant.v();
                        Type returnType = method.getReturnType();
                        if (returnType instanceof RefType) {
                            v = NullConstant.v();
                        } else if (returnType instanceof IntType) {
                            v = IntConstant.v(0);
                        } else if (returnType instanceof LongType) {
                            v = LongConstant.v(0);
                        } else if (returnType instanceof DoubleType) {
                            v = DoubleConstant.v(0);
                        } else if (returnType instanceof FloatType) {
                            v = FloatConstant.v(0);
                        } else if (returnType instanceof BooleanType) {
                            v = IntConstant.v(0);
                        } else if (returnType instanceof CharType) {
                            v = IntConstant.v(0);
                        } else if (returnType instanceof ByteType) {
                            v = IntConstant.v(0);
                        } else if (returnType instanceof ShortType) {
                            v = IntConstant.v(0);
                        } else if (returnType instanceof VoidType) {
                            v = NullConstant.v();
                        }
                        returnStmt.setOp(v);
                        continue;
                    }
                    toRemoveStmts.add(stmt);
                }
            }
            for (Stmt stmt : toRemoveStmts) {
                units.remove(stmt);
            }
        }
    }

    public Set<String> getRemovedCounter() {
        return removedCounter;
    }

    public Set<String> getTotalCounter() {
        return totalCounter;
    }
}
