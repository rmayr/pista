/*
** OwnTracks job selector UI
** Author: Ben Jones
*/
#include <avr/wdt.h>
#include <LiquidCrystal.h>
#include "ClickButton.h"

// GW serial password
#define GW_PASSWORD             1234567890

// timeouts and buffer lengths
#define COMMAND_PERIOD          1000
#define RX_BUFFER_LEN           200

// mqtt constants
#define MQTT_SUB_QOS            0
#define MQTT_PUB_QOS            2
#define MQTT_PUB_RETAIN         1

// lcd
#define LCD_CHARS               20
#define LCD_LINES               4
#define JOB_ACTIVE_ACK_TIMEOUT  20000
#define JOB_ACTIVE_VIEW_REFRESH 1000

// job constraints
#define MAX_JOB_COUNT           16
#define MAX_JOB_NAME_LEN        LCD_CHARS - 1
#define JOB_INACTIVE            0

#define LED_PIN                 13
#define LED_BLINK_PERIOD        1000
#define LED_OFF                 0
#define LED_ON                  1
#define LED_BLINK               2

// rotary encoder
#define ENC_PORT                PINC
#define ENC_A                   14
#define ENC_B                   15
#define ENC_BUTTON              3

// initialize the library with the interface pins
LiquidCrystal lcd(7, 8, 9, 10, 11, 12);

// encoder button
ClickButton encoderButton(ENC_BUTTON, LOW, CLICKBTN_PULLUP);

// list of job names
char jobNames[MAX_JOB_COUNT][MAX_JOB_NAME_LEN];
int jobCount = 0;

// is MQTT is up and available
byte mqtt = 0;
// have we subscribed to the jobs list topic
byte subJobList = 0;
// have we subscribed to the command topic
byte subCommand = 0;

// rx buffer
char rxData[RX_BUFFER_LEN];
bool newRxData = false;

// keep track of the last time we sent a command to GW 
long commandLast = 0;

// lcd state variables
char lcdLines[LCD_LINES][LCD_CHARS];
byte lcdNeedsUpdating = 0;
int lineSelected = 0;

// job state variables
int jobDisplayList[LCD_LINES];
byte jobListUpdated = 0;
int jobSelectionChanged = 0;

int jobActive = JOB_INACTIVE;
long jobActiveFrom = 0;
byte jobActiveWaitingAck = 0;
long jobActiveWaitingAckFrom = 0;

// LED variables (0=off, 1=on, 2=blink)
int ledState = LED_OFF;
long ledBlinkLast = 0;

void setup() {
  // ensure the watchdog is disabled
  wdt_disable();

  // GW serial port is 115200
  Serial.begin(115200);

  // set up the lcd
  lcd.begin(LCD_CHARS, LCD_LINES);
  printStatus("starting up");
  
  // initialise our encoder pins as inputs
  pinMode(ENC_A, INPUT_PULLUP);
  pinMode(ENC_B, INPUT_PULLUP);
  pinMode(ENC_BUTTON, INPUT_PULLUP);

  // initialise our LED
  pinMode(LED_PIN, OUTPUT);

  // enable the watch dog timer - 8s timeout
  wdt_enable(WDTO_8S);
  wdt_reset();
}

void loop() {
  // if we take too long to connect to the GW MQTT proxy
  // then restart via the watchdog timer (8s)
  if (mqtt) { wdt_reset(); }
  
  // initialise connection to the GW
  initialiseGw();

  // check for data on the GW serial bus and handle
  receiveGwData();
  handleGwData();
  
  // see if our encoder has changed
  handleEncoder();
  
  // check our job active ack timeout
  checkJobActiveAck();

  // update lcd
  updateLcd();
  
  // update the LED
  updateLed();
}

void initialiseGw() {
  // is MQTT up on the GW?
  if (!mqtt && commandReady()) {
    sendGwMqtt();
  }
  
  // have we subscribed to the job list topic yet?
  if (mqtt && !subJobList && commandReady()) {
    sendGwSubJobs();
  }  

  // have we subscribed to the command topic yet?
  if (mqtt && !subCommand && commandReady()) {
    sendGwSubCommand();
  }  
}

bool commandReady() {
  return (millis() - commandLast) > COMMAND_PERIOD;
}

void reconnectGw() {
  // reset the MQTT connection flag to force a reconnect
  mqtt = 0;
  // reset our job state
  jobActive = JOB_INACTIVE;
  jobActiveFrom = 0;
  jobActiveWaitingAck = 0;
  jobActiveWaitingAckFrom = 0;
  // indicate there was a problem
  ledState = LED_BLINK;  
}

void receiveGwData() {
  // need to detect MQTT messages and the NAK failure event
  static char msgMarker = '<';
  static char NAKMarker = 'N';
  static char eolMarker = '\r';
	
  static boolean rxInProgress = false;
  static int rxIndex = 0;
  char data;

  while (Serial.available() > 0 && !newRxData) {
    // read the next char
    data = Serial.read();
    // check for markers and populate are rx array
    if (rxInProgress) {
      if (data == eolMarker) {
        rxData[rxIndex] = '\0';
        rxIndex = 0;
        rxInProgress = false;
        newRxData = true;
      } else {
        rxData[rxIndex++] = data;
        if (rxIndex >= RX_BUFFER_LEN) {
          rxIndex = RX_BUFFER_LEN - 1;
        }
      }
    } else if (data == msgMarker || data == NAKMarker) {
      rxData[rxIndex++] = data;
      rxInProgress = true;
    }
  }
}

void handleGwData() {
  // ignore if nothing to do
  if (!newRxData) 
    return;
  
  // handle the new data
  if (strncmp(rxData, "NACK", 4) == 0) {
    handleGwNAK();
  } else if (strncmp(rxData, "< MQTT", 6) == 0) {
    handleGwMqtt(rxData);
  } else if (strncmp(rxData, "< jobs/active", 13) == 0) {
    handleGwJobActive(rxData);
  } else if (strncmp(rxData, "< jobs/", 7) == 0) {
    handleGwJob(rxData);
  } else if (strncmp(rxData, "< cmd", 5) == 0) {
    handleGwCommand(rxData);
  } else {
    printStatus(rxData);
  }
  
  // finished with this data
  newRxData = false;
}

// GW command methods (send/handle)
void sendGwLogin() {
  Serial.print("login ");
  Serial.println(GW_PASSWORD);
}

void sendGwMqtt() {
  // always login before each command
  sendGwLogin();
  // request the MQTT status from the GW
  Serial.println("mqtt");
  // mqtt flag is set by MQTT ACK
  printStatus("checking mqtt");
  commandLast = millis();
}

void sendGwSubJobs() {
  // always login before each command
  sendGwLogin();
  // subscribe to the job list
  if (sendMqttSub("jobs/+")) {
    printStatus("subscribed jobs/+");
    // no SUB ACK but only want to subscribe once
    subJobList = 1;
  }
  commandLast = millis();
}

void sendGwSubCommand() {
  // always login before each command
  sendGwLogin();
  // subscribe to the command topic
  if (sendMqttSub("cmd")) {
    printStatus("subscribed cmd");
    // no SUB ACK but only want to subscribe once
    subCommand = 1;
  }
  commandLast = millis();
}

void handleGwNAK() {
  // could be MQTT is down or something else is wrong - reconnect
  reconnectGw();
}

void handleGwMqtt(char * data) {
  // '< MQTT 1|0'
  mqtt = data[7] == '1';
  if (mqtt) {
    printStatus("mqtt up");
  } else {
    printStatus("mqtt down");
  }
  // whenever the MQTT status changes we reset the subscription flags
  subJobList = 0;
  subCommand = 0;
}

void handleGwJobActive(char * data) {
  // '< jobs/active <job>'
  // skip the sub-topic name
  char * p = data + 14;
  // extract the job number from the payload
  int job = parseInt(p);
  if (job > MAX_JOB_COUNT) {
    return;
  }
  // if we are waiting for an ack then handle 
  // otherwise the active job has changed externally
  if (jobActiveWaitingAck) {
    // some sort of ack received
    jobActiveWaitingAck = 0;
    if (jobActive != job) {
      // re-publish the active job
      updateJobActive(jobActive);
      // indicate there was a problem
      ledState = LED_BLINK;
    } else {
      // ack is ok
      lcdNeedsUpdating = 1;
      // indicate everything is ok
      ledState = LED_OFF;
    }
  } else {
    jobActive = job;
    jobActiveFrom = millis();
    lcdNeedsUpdating = 1;
  }
}

void handleGwJob(char * data) {
  // '< jobs/x <name>'
  // skip the sub-topic name
  char * p = data + 7;
  // extract the job number from the topic
  int job = parseInt(p);
  if (job > MAX_JOB_COUNT) {
    return;
  }
  // get the payload
  p = strchr(p, ' ') + 1;
  // copy to our job and update our counter
  strncpy(jobNames[job - 1], p, MAX_JOB_NAME_LEN);
  if (strlen(jobNames[job - 1]) == 0) {
    jobCount--;
  } else {
    jobCount++;
  }
  // we need to refresh the job list
  jobListUpdated = 1;
  lcdNeedsUpdating = 1;
}

void handleGwCommand(char * data) {
  // '< cmd <command>'
  // skip the sub-topic name
  char * p = data + 6;
  // handle command
  if (strncmp(p, "led-off", 7) == 0) {
    ledState = LED_OFF;
  } else if (strncmp(p, "led-on", 6) == 0) {
    ledState = LED_ON;
  } else if (strncmp(p, "led-blink", 9) == 0) {
    ledState = LED_BLINK;
  } else if (strncmp(p, "gpio", 4) == 0) {
    // gpio<pin>-<value>
    int gpio = parseInt(p + 4);
    pinMode(gpio, OUTPUT);
    // HIGH is off, LOW is on
    char * value = strchr(p, '-') + 1;
    digitalWrite(gpio, value[0] == '0' ? HIGH : LOW); 
  }
}

bool sendMqttSub(char * topic) {
  // can't do anything until MQTT is up
  if (!mqtt) {
    printStatus("mqtt down, reconnect");
    return false;
  }
  // always login before each command
  sendGwLogin();
  // sub <qos> <topic>
  Serial.print("sub ");
  Serial.print(MQTT_SUB_QOS);
  Serial.print(" ");
  Serial.println(topic);
  return true;
}

bool sendMqttPub(char * topic, int payload) {
  // can't do anything until MQTT is up
  if (!mqtt) {
    printStatus("mqtt down, reconnect");
    return false;
  }
  // always login before each command
  sendGwLogin();
  // pub <qos> <topic> <retain> <message>
  Serial.print("pub ");
  Serial.print(MQTT_PUB_QOS);
  Serial.print(" ");
  Serial.print(topic);
  Serial.print(" ");
  Serial.print(MQTT_PUB_RETAIN);
  Serial.print(" ");
  Serial.println(payload);
  return true;
}

int parseInt(char * p) {
  if (strlen(p) == 0)
    return 0;
  static char number[4];
  int digit = 0;
  if (p[0] == '-') {
    number[0] = '-';
    digit++; 
  }
  while (isdigit(p[digit])) {
    number[digit] = p[digit];
    number[++digit] = '\0';
  }
  return atoi(number);
}

void checkJobActiveAck() {
  if (jobActiveWaitingAck) {
    if ((millis() - jobActiveWaitingAckFrom) > JOB_ACTIVE_ACK_TIMEOUT) {
      // we have timed out waiting for an ACK so reset our connection
      // to the GW and start over
      reconnectGw();
    }
  }
}

void updateLcd() {
  // if our update flag is set then always refresh
  if (!lcdNeedsUpdating) {
    // otherwise update every second if we have an active job
    if ((jobActive == JOB_INACTIVE) || (((millis() - jobActiveFrom) % JOB_ACTIVE_VIEW_REFRESH) != 0)) {
      return;
    }
  }
  
  // update our display depending on what mode we are in
  if (jobActive == JOB_INACTIVE) {
    displayJobList();
  } else {
    displayJobActive();
  }
  
  // update the lcd lines 
  lcd.clear();
  for (int line = 0; line < LCD_LINES; line++) {
    printLcd(lcdLines[line], line);
  }

  // done refreshing the lcd
  lcdNeedsUpdating = 0;
}

void updateLed() {
  // handle any changes in the LED state
  if (ledState == LED_OFF) {
    digitalWrite(LED_PIN, LOW);
  } else if (ledState == LED_ON) {
    digitalWrite(LED_PIN, HIGH);
  } else if (ledState == LED_BLINK) {
    if ((millis() - ledBlinkLast) > LED_BLINK_PERIOD) {
      static int ledBlink = HIGH;
      if (ledBlink == HIGH) {
        ledBlink = LOW;
      } else {
        ledBlink = HIGH;
      }
      digitalWrite(LED_PIN, ledBlink);
      ledBlinkLast = millis();
    }
  }
}

void displayJobActive() {
  // millisecond periods
  static long hour = 3600000;
  static long minute = 60000;
  static long second = 1000;

  // job name
  displayJob(jobActive, 0);
  lcdLines[0][0] = '>';
  // active time
  long activeElapsed = millis() - jobActiveFrom;
  
  int hours = activeElapsed / hour;
  int minutes = (activeElapsed % hour) / minute;
  int seconds = ((activeElapsed % hour) % minute) / second;
  if (hours == 0 && minutes == 0) {
    snprintf(lcdLines[1], LCD_CHARS, " active %ds", seconds);
  } else if (hours == 0) {
    snprintf(lcdLines[1], LCD_CHARS, " active %dm %ds", minutes, seconds);
  } else {
    snprintf(lcdLines[1], LCD_CHARS, " active %dh %dm", hours, minutes);
  }
  // empty line 
  lcdLines[2][0] = '\0';
  // exit hint
  if (jobActiveWaitingAck == 0) {
    strncpy(lcdLines[3], " Dbl-click to STOP", LCD_CHARS);
  } else {
    lcdLines[3][0] = '\0';
  }
}

void displayJobList() {
  static int line;

  // if the job list has been updated then re-populate from scratch
  if (jobListUpdated) {
    for (line = 0; line < LCD_LINES; line++) {
      jobDisplayList[line] = JOB_INACTIVE;
    }
    for (line = 0; line < LCD_LINES; line++) {
      jobDisplayList[line] = getNextJobDisplay(0);
    }
    lineSelected = 0;
  }

  // if the selection has changed move the cursor
  int jobListChanged = 0;
  if (jobSelectionChanged > 0) {
    if (jobCount <= 4) {
      if (lineSelected == jobCount - 1) {
        lineSelected = 0;
      } else {
        lineSelected++;
      }
    } else {
      if (lineSelected == LCD_LINES - 1) {
        jobListChanged++;
      } else {
        lineSelected++;
      }
    }  
  } else if (jobSelectionChanged < 0) {
    if (jobCount <= 4) {
      if (lineSelected == 0) {
        lineSelected = jobCount - 1;
      } else {
        lineSelected--;
      }
    } else {
      if (lineSelected == 0) {
        jobListChanged--;
      } else {
        lineSelected--;
      }
    }
  }
  
  // if the list needs to change then handle
  if (jobListChanged > 0) {
    for (line = 0; line < (LCD_LINES - 1); line++) {
      jobDisplayList[line] = jobDisplayList[line + 1];
    }
    jobDisplayList[LCD_LINES - 1] = getNextJobDisplay(jobDisplayList[LCD_LINES - 2]);
  } else if (jobListChanged < 0) {
    for (line = (LCD_LINES - 1); line > 0; line--) {
      jobDisplayList[line] = jobDisplayList[line - 1];
    }
    jobDisplayList[0] = getPrevJobDisplay(jobDisplayList[1]);
  }
  
  // update the lcd lines 
  for (line = 0; line < LCD_LINES; line++) {
    displayJob(jobDisplayList[line], line);
  }
  
  jobListUpdated = 0;  
  jobSelectionChanged = 0;  
}

int getNextJobDisplay(int job) {
  for (int i = 0; i < MAX_JOB_COUNT; i++) {
    job = getNextJobIndex(job);
    if (isJobDisplayable(job)) { return job; }
  }  
  return JOB_INACTIVE;
}

int getPrevJobDisplay(int job) {
  for (int i = 0; i < MAX_JOB_COUNT; i++) {
    job = getPrevJobIndex(job);
    if (isJobDisplayable(job)) { return job; }
  }  
  return JOB_INACTIVE;
}

int getNextJobIndex(int job) {
  if (job >= MAX_JOB_COUNT) {
    return 1;
  }
  return job + 1;
}

int getPrevJobIndex(int job) {
  if (job == 1) {
    return MAX_JOB_COUNT;
  }
  return job - 1;
}

byte isJobDisplayable(int job) {
  // check if this job is already being displayed
  for (int line = 0; line < LCD_LINES; line++) {
    if (jobDisplayList[line] == job) { return 0; } 
  }
  // check if this job is displayable
  return strlen(jobNames[job - 1]) > 0;
}

void displayJob(int job, int line) {
  char * p = lcdLines[line];
  if (job == JOB_INACTIVE || strlen(jobNames[job - 1]) == 0) {
    p[0] = '\0';
  } else {
    if (line == lineSelected) {
      snprintf(p, LCD_CHARS, ">%s", jobNames[job - 1]);
    } else {
      snprintf(p, LCD_CHARS, " %s", jobNames[job - 1]);
    }
  }
}

void printStatus(char * status) {
  // print status to LCD for now
  lcd.clear();
  printLcd(status, 0);
}

void printLcd(char * text, int line) {
  static char display[LCD_CHARS];
  strncpy(display, text, LCD_CHARS);
  lcd.setCursor(0, line);
  lcd.print(text);
}

void handleEncoder() {
  // this variable will be changed by encoder input
  static int8_t counter = 0;
  
  // ignore the encoder if we have an active job
  if (jobCount > 0 && (jobActive == JOB_INACTIVE)) {
    // the encoder will report 4 increments per click
    counter += readEncoder();
    
    // update our selected job index
    if (counter <= -4) {
      jobSelectionChanged = -1;
      lcdNeedsUpdating = 1;
      counter = 0;
    } else if (counter >= 4) {
      jobSelectionChanged = 1;
      lcdNeedsUpdating = 1;
      counter = 0;
    }
  }
  
  // read the button state
  encoderButton.Update();

  // handle the button events
  if (encoderButton.clicks == 1 && (jobActive == JOB_INACTIVE)) {
    updateJobActive(jobDisplayList[lineSelected]);
  } else if (encoderButton.clicks == 2 && (jobActive != JOB_INACTIVE)) {
    updateJobActive(JOB_INACTIVE);
  }
}

void updateJobActive(int job) {
  if (jobCount == 0) {
    // if no jobs then ignore
    printStatus("no jobs loaded");
  } else if (jobActiveWaitingAck) {
    // if we are still waiting for an ack then ignore
    printStatus("please wait...");
  } else {
    // publish the new active job and set our job state variables
    if (sendMqttPub("jobs/active", job)) {
      jobActive = job;
      jobActiveFrom = millis();
      jobActiveWaitingAck = 1;
      jobActiveWaitingAckFrom = millis();
      lcdNeedsUpdating = 1;
    }
  }
}

int8_t readEncoder()
{
  static int8_t enc_states[] = {0,-1,1,0,1,0,0,-1,-1,0,0,1,0,1,-1,0};
  static uint8_t old_AB = 0;
  // remember previous state
  old_AB <<= 2;
  // add current state
  old_AB |= ( ENC_PORT & 0x03 );
  // get change in state (-1, 0, 1)
  return enc_states[( old_AB & 0x0f )];
}
