import jpype
import os

def start_jvm(extra_jars=None):
    if jpype.isJVMStarted():
        return

    if extra_jars is None:
        extra_jars = []

    jars = [
        os.path.abspath("libs/jt400.jar"),
        os.path.abspath("libs/fmjdbc.jar"),  # your FileMaker JDBC
    ] + [os.path.abspath(p) for p in extra_jars]

    classpath = ":".join(jars)

    jpype.startJVM(
        jpype.getDefaultJVMPath(),
        "-Djava.class.path=" + classpath,
        convertStrings=True,
    )
