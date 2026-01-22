call ndk-build clean
call ndk-build TARGET_LINK=0 NDK_DEBUG=0 CONFIGURATION=StaticRelease
call ndk-build TARGET_LINK=0 NDK_DEBUG=1 CONFIGURATION=StaticDebug
rmdir /s /q libs
rmdir /s /q obj
call ndk-build clean
call ndk-build TARGET_LINK=1 NDK_DEBUG=0 CONFIGURATION=DynamicRelease
call ndk-build TARGET_LINK=1 NDK_DEBUG=1 CONFIGURATION=DynamicDebug
rmdir /s /q libs
rmdir /s /q obj
rem xcopy /y ..\..\..\..\BuildFiles\Android\arm64-v8a\StaticRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.a %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\arm64-v8a\StaticRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\arm64-v8a\DynamicRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.so %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\arm64-v8a\DynamicRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\armeabi\StaticRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.a %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\armeabi\StaticRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\armeabi\DynamicRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.so %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\armeabi\DynamicRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\armeabi-v7a\StaticRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.a %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\armeabi-v7a\StaticRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\armeabi-v7a\DynamicRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.so %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\armeabi-v7a\DynamicRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\mips\StaticRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.a %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\mips\StaticRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\mips\DynamicRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.so %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\mips\DynamicRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\mips64\StaticRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.a %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\mips64\StaticRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\mips64\DynamicRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.so %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\mips64\DynamicRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\x86\StaticRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.a %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\x86\StaticRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\x86\DynamicRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.so %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\x86\DynamicRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\x86_64\StaticRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.a %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\x86_64\StaticRelease\
rem xcopy /y ..\..\..\..\BuildFiles\Android\x86_64\DynamicRelease\lib6E5C5B7C979F40108F7CDC08EADFB777.so %ECO_FRAMEWORK%\Eco.AI.Engine1\BuildFiles\Android\x86_64\DynamicRelease\
pause
