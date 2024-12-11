set arg1=%1
shift
set params=%1
:loop
shift
if [%1]==[] goto afterloop
set params=%params% %1
goto loop
:afterloop
manimgl .\musimation.py Musimation -w %params%
ffmpeg -y -i .\media\Musimation.mp4 -i C:\Users\iarju\Downloads\%arg1% -filter_complex "[1:a]adelay=5000|5000[aud];[0:v][aud]concat=n=1:v=1:a=1[v][a]" -map "[v]" -map "[a]" .\media\Musimation_with_audio.mp4