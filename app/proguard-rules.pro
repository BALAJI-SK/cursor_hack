# Keep all JNI native method signatures (TFLite, 7-Zip-JBinding).
-keepclasseswithmembernames class * {
    native <methods>;
}

# 7-Zip-JBinding (JNI callbacks must be kept)
-keep class net.sf.sevenzipjbinding.** { *; }
-dontwarn net.sf.sevenzipjbinding.**

# commons-compress
-dontwarn org.apache.commons.compress.**

# TensorFlow Lite
-keep class org.tensorflow.lite.** { *; }
-dontwarn org.tensorflow.lite.**
