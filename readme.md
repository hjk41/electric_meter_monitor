# [WIP] Old-style Electric Meter Reading And Notification System
[中文版](#旧式电表读数和通知系统)


If you have an old-style electric meter like mine, which cannot be read or recharged online, you can use this system to read the meter and notify you when the remaining electricity is low.

## What this system does?

1. Take a photo of the electric meter using ESP32-CAM periodically. The code for the ESP32-CAM is in the `cam` folder. 

2. ESP32-CAM sends the photo to a server. The code for the server is in the `web` folder.

3. The server reads the reading of the electric meter from the photo using DashScope LLM, say `1000` kWh.

4. At the first use, you will need to manually input the remaining balance for your electric meter, say `123` kWh, and the threshold for sending notifications, say `10` kWh.

5. Each time the server reads the electric meter, it will compare the reading with the remaining balance. If the remaining balance is less than a threshold, which you can set, it will send you a notification via vxpush.

## How to use this project?

1. Get a ESP32-CAM module. You can buy it from Taobao.com or AliExpress.

2. Setup ESP32-CAM module.
    - Open cam/cam.ino with Arduino IDE.
    - In the `Select Board` dropdown, choose `ESP32 Dev Module`.
    - Copy `cam/config.h.sample` to `config.h`, and open it. Then modify the ssid, password and serverUrl. The ESP32 module will connect to this ssid and upload the photo of your electric meter to the serverUrl. The serverUrl is the address of the web server you will start in the next step.
    - In Tools->ESPRAM, choose `Enable`.
    - Build and upload the code into ESP32-CAM.
    - You should see the flash light on the module flash, and then ESP32-CAM should go to sleep for 24 hours.

3. Setup web server.
    - Install python3 and required packages with `pip install -r requirements.txt`.
    - Start web server on a machine with `python web/run_server.py`. You must keep this server running. The camera will upload pictures to this server once a day.
    - If successful, you should be able to visit this server and manually upload pictures to it.

4. [Optional] 3D print a container for the camera and battery. I have designed one with onshape.com, you can fork it if you need modification: [3D model.](
https://cad.onshape.com/documents/f7c3da0e53b1b43bbca61603/w/b6e964f581bf2b84816ed299/e/2a72d19ce90953db3887327b?renderMode=0&uiState=66eec0c262bb94758fb1929b)

5. Power on the ESP32-CAM, and keep it running. Since the ESP32-CAM module consumes very little power during deep sleep, you can use battery and it should last for quite a long time.

---------------------------
# 旧式电表读数和通知系统

如果您有像我一样的旧式电表，无法在线读取或充值，您可以使用此系统读取电表并在剩余电量低时通知您。

## 这个系统做什么？

1. 使用ESP32-CAM定期拍摄电表的照片。ESP32-CAM的代码在`cam`文件夹中。

2. ESP32-CAM将照片发送到服务器。服务器的代码在`web`文件夹中。

3. 服务器使用DashScope LLM从照片中读取电表的读数，比如`1000`千瓦时。

4. 在第一次使用时，您需要手动输入电表的剩余余额，比如`123`千瓦时，以及发送通知的阈值，比如`10`千瓦时。

5. 每次服务器读取电表时，它将比较读数和剩余余额。如果剩余余额低于您可以设置的阈值，它将通过vxpush向您发送通知。

## 如何使用这个项目？

1. 获取一个ESP32-CAM模块。您可以从淘宝网或AliExpress购买。

2. 设置ESP32-CAM模块。
    - 使用Arduino IDE打开`cam/cam.ino`。
    - 在`选择板`下拉菜单中，选择`ESP32 Dev Module`。
    - 复制`cam/config.h.sample`到`config.h`，并打开它。然后修改ssid、密码和serverUrl。ESP32模块将连接到这个ssid并将电表的照片上传到serverUrl。serverUrl是您将在下一步启动的web服务器的地址。
    - 在工具->ESPRAM中，选择`启用`。
    - 构建并上传代码到ESP32-CAM。
    - 您应该看到模块上的闪光灯闪烁，然后ESP32-CAM将进入24小时的睡眠状态。

3. 设置web服务器。
    - 使用`pip install -r requirements.txt`安装python3和所需的包。
    - 在一台机器上使用`python web/run_server.py`启动web服务器。您必须保持此服务器运行。相机将每天上传图片到此服务器。
    - 如果成功，您应该能够访问此服务器并手动上传图片。

4. [可选] 3D打印一个相机和电池的容器。我使用onshape.com设计了一个，如果您需要修改，可以fork它：[3D模型。](https://cad.onshape.com/documents/f7c3da0e53b1b43bbca61603/w/b6e964f581bf2b84816ed299/e/2a72d19ce90953db3887327b?renderMode=0&uiState=66eec0c262bb94758fb1929b)

5. 打开ESP32-CAM电源，并保持其运行。由于ESP32-CAM模块在深度睡眠期间消耗非常少的电量，您可以使用电池，并且它应该可以持续很长时间。



