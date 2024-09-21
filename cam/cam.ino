#include <Arduino.h>
#include "esp_camera.h"
#include "WiFi.h"
#include "HTTPClient.h"
#include "base64.h"
#include "driver/rtc_io.h"

#include "config.h"

// Camera pin definitions
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#define LAMP_PIN           4 // LED FloodLamp.

const long long sleep_s = 24*3600;

void forceSleep(void*) {
  Serial.println("Forcing sleep...");
  digitalWrite(33, LOW);
  rtc_gpio_isolate(GPIO_NUM_4);
  esp_sleep_enable_timer_wakeup(sleep_s * 1000000);
  esp_deep_sleep_start();
}

void InitCamera() {
  // Configure camera settings
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_SVGA;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  //config.fb_location = CAMERA_FB_IN_DRAM;

  // Camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  // Most OV cameras produces images upside down, we need to flip it
  sensor_t * s = esp_camera_sensor_get();
  s->set_vflip(s, 1); // flip it vertically
  s->set_hmirror(s, 1); // flip it horizontally
}

void StopCamera() {
  esp_camera_deinit();
}

void InitWiFi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");
}

void StopWiFi() {
  WiFi.disconnect(true);
}

String TakePicture() {
  rtc_gpio_hold_dis(GPIO_NUM_4);
  
  // Most OV cameras produces images upside down, we need to flip it
  sensor_t * s = esp_camera_sensor_get();
  s->set_vflip(s, 1); // flip it vertically
  s->set_hmirror(s, 1); // flip it horizontally
  
  // Take Picture with Camera
  // use maximum flash light
  pinMode(LAMP_PIN, OUTPUT);
  digitalWrite(LAMP_PIN, HIGH);
  delay(10);
  camera_fb_t * fb = esp_camera_fb_get();
  if(!fb) {
    Serial.println("Camera capture failed");
    return String();
  }
  // turn off flash light
  digitalWrite(LAMP_PIN, LOW);

  String pic(fb->buf, fb->len);
  // Return the frame buffer back to the driver for reuse
  esp_camera_fb_return(fb);
  rtc_gpio_isolate(GPIO_NUM_4);
  return pic;
}

esp_timer_handle_t CreateForceSleepTimer() {
  esp_timer_handle_t force_sleep_timer;
  esp_timer_create_args_t fs_timer_args = {
    .callback = &forceSleep,
    .name = "force_sleep"
  };
  esp_timer_create(&fs_timer_args, &force_sleep_timer);
  esp_timer_start_once(force_sleep_timer, 20 * 1000000);  // put to sleep if we are still running after 20 seconds
  return force_sleep_timer;
}

void SendPicture(const String& pic) {
  // Upload picture to server
  if(WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl); // Specify the URL

    // Prepare form-data
    String boundary = "---------------------------14737809831466499882746641449";
    String body = "--" + boundary + "\r\n";
    body += "Content-Disposition: form-data; name=\"user_id\"\r\n\r\n";
    body += "002\r\n"; // User ID
    body += "--" + boundary + "\r\n";
    body += "Content-Disposition: form-data; name=\"file\"; filename=\"image.jpg\"\r\n";
    body += "Content-Type: image/jpeg\r\n\r\n";

    // Send the header
    http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

    // Send the body
    int httpResponseCode = http.POST(body + pic + "\r\n--" + boundary + "--\r\n");
    if (httpResponseCode > 0) {
        Serial.printf("HTTP Response code: %d\n", httpResponseCode);
    } else {
        Serial.printf("Error code: %d\n", httpResponseCode);
    }
    http.end();
  } else {
    Serial.println("WiFi Disconnected");
  }
}

void setup() {
  // Initialize Serial Monitor
  Serial.begin(115200);
  Serial.println("Starting ESP32-CAM...");

  // set timer to force sleep
  esp_timer_handle_t force_sleep_timer = CreateForceSleepTimer();

  // Initialize Camera
  InitCamera();
  // Take Picture
  String pic = TakePicture();
  // Initialize WiFi
  InitWiFi();
  // Send Picture
  SendPicture(pic);
  // Stop WiFi
  StopWiFi();
  // Stop Camera
  StopCamera();

  // disable force sleep timer
  esp_timer_stop(force_sleep_timer);

  // hibernate for 1 day
  esp_sleep_enable_timer_wakeup(sleep_s * 1000000);
  esp_deep_sleep_start();
}

void loop() {
}