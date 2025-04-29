# delpoy but run failed

1
1. yt-dlp 下载失败， 【修复】添加cookie 设置
ERROR: [youtube] gl1r1XV0SLw: Sign in to confirm you’re not a bot. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies


cursor：
https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp

yt-dlp --cookies-from-browser chrome --cookies cookies.txt. yt-dlp will extract the browser cookies and save them to the filepath specified after --cookies. The resulting text file can then be used with the --cookies option. Note though that this method exports your browser's cookies for ALL sites (even if you passed a URL to yt-dlp), so take care in not letting this text file fall into the wrong hands.

2. 下载的文件没有字幕
直接从音频转录

3. AI setting
就用deepseek 试试

用 阿里的 百炼平台

成功了，耗时较长，output 目录下带sub 的mp4 文件

4. 如何去水印



5. 如何替换 人物  

https://modelscope.cn/studios/Damo_XR_Lab/motionshop/summary
https://modelscope.cn/studios/Damo_XR_Lab/Motionshop2

有时间限制， 让我截取20s 视频实施
ffmpeg -i output/output_sub.mp4 -t 20 -c copy output/output_sub_20s.mp4

替换不对，应该先替换人物再驱动

暂时没有找到开源方案， 可以使用

https://github.com/ai-aigc-studio/Viggle-AI-WebUI?tab=readme-ov-file

Viggle  的效果还可以

后面看看数字人技术 HeyGem livePortrait

https://www.youtube.com/watch?v=4CqcVmx713w

# 热门项目排行榜
https://www.aibase.com/zh/repos/ranking/project

自媒体

https://github.com/ddean2009/MoneyPrinterPlus

https://www.youtube.com/channel/UCOB2vNtTrzMRMEwdwV5eMOQ

换脸

https://github.com/lightbatis/DeepLiveCam

https://juejin.cn/post/7437533313773092900

