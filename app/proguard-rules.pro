# Keep model classes used by Room
-keep class com.hypemarketer.callvault.data.db.** { *; }

# Google API client
-keep class com.google.api.** { *; }
-keep class com.google.api.client.** { *; }
-dontwarn com.google.api.client.**
-dontwarn org.apache.http.**

# Generative AI SDK
-keep class com.google.ai.client.generativeai.** { *; }
