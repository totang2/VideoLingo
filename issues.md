# delpoy but run failed

1

3. AI setting
就用deepseek 试试

用 阿里的 百炼平台

成功了，耗时较长，output 目录下带sub 的mp4 文件


# 热门项目排行榜
https://www.aibase.com/zh/repos/ranking/project

自媒体

https://github.com/ddean2009/MoneyPrinterPlus

https://github.com/FujiwaraChoki/MoneyPrinterV2



https://www.youtube.com/channel/UCOB2vNtTrzMRMEwdwV5eMOQ

换脸

https://github.com/lightbatis/DeepLiveCam

https://juejin.cn/post/7437533313773092900


# 尝试 huggingface 
上面的 image segment 模型很多都能很好完成这个抠图工作，证明了思路是对的。

只需提示词：搽除右下角的 画中画。

但是目前对模型的使用， 需要继续调研。如何指定分割区域。带限定搽除特定对象。sam 的学习， track object 在视频。

如何获得背景。
- 识别区域



- 搽除后的修复。

例如： https://backgrounderase.net/home

阅读论文


接下来的工作就是 图像的分割， 合成，伪造

这里有个修复例子

https://medium.com/@bhatadithya54764118/day-93-advanced-video-object-removal-using-deep-learning-8cf028ca5764



# 排查配音没有的问题

1. 产生了 output/dub.mp3

检查格式
```
ffprobe -v error -show_entries stream=codec_type,codec_name,channels,sample_rate -of default=noprint_wrappers=1 "/Users/always_day_1/work/VideoLingo/output/dub.mp3"

codec_name=mp3
codec_type=audio
sample_rate=16000
channels=1
```

检查音量
```
ffmpeg -i "/Users/always_day_1/work/VideoLingo/output/dub.mp3" -af "volumedetect" -f null -

```

增加音量
```
ffmpeg -i "/Users/always_day_1/work/VideoLingo/output/dub.mp3" -filter:a "volume=2.0" "/Users/always_day_1/work/VideoLingo/output/dub_louder.mp3"

ffmpeg -i "/Users/always_day_1/work/VideoLingo/output/dub.mp3" -filter:a "volume=20dB" "/Users/always_day_1/work/VideoLingo/output/dub_louder.mp3"
```

还是不行，检查tts 生成过程：
```
ls -l output/audio/tts_tasks.xlsx
```

任务分片没有问题

```
ls -l output/audio/segs/
ls -l output/audio/tmp/
```

这里面的wav 文件都是没有声音的，tts 应该没有成功执行


```
rm -rf ./out/audio/tmp/
python ./core/step10_gen_audio.py
```