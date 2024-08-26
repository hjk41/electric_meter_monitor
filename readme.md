# Old-style Electric Meter Reading And Notification System
[中文版](#旧式电表读数和通知系统)


If you have an old-style electric meter like mine, which cannot be read or recharged online, you can use this system to read the meter and notify you when the remaining electricity is low.

## What this system does?

1. Take a photo of the electric meter using ESP32-CAM periodically. The code for the ESP32-CAM is in the `cam` folder. 

2. ESP32-CAM sends the photo to a server. The code for the server is in the `web` folder.

3. The server reads the reading of the electric meter from the photo using DashScope LLM, say `1000` kWh.

4. At the first use, you will need to manually input the remaining balance for your electric meter, say `123` kWh, and the threshold for sending notifications, say `10` kWh.

5. Each time the server reads the electric meter, it will compare the reading with the remaining balance. If the remaining balance is less than a threshold, which you can set, it will send you a notification via vxpush.

---------------------------
# 旧式电表读数和通知系统

如果您有像我一样的旧式电表，无法在线读取或充值，您可以使用此系统读取电表并在剩余电量低时通知您。

## 这个系统做什么？

1. 使用ESP32-CAM定期拍摄电表的照片。ESP32-CAM的代码在`cam`文件夹中。

2. ESP32-CAM将照片发送到服务器。服务器的代码在`web`文件夹中。

3. 服务器使用DashScope LLM从照片中读取电表的读数，比如`1000`千瓦时。

4. 在第一次使用时，您需要手动输入电表的剩余余额，比如`123`千瓦时，以及发送通知的阈值，比如`10`千瓦时。

5. 每次服务器读取电表时，它将比较读数和剩余余额。如果剩余余额低于您可以设置的阈值，它将通过vxpush向您发送通知。







