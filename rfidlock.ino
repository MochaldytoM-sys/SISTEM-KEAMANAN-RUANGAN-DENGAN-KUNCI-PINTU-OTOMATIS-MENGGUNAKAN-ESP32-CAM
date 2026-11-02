#include <SPI.h>
#include <MFRC522.h>

// =================================
// KONFIGURASI RFID
// =================================

#define RFID_SS_PIN   5
#define RFID_RST_PIN  22

MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);

// =================================
// KONFIGURASI SOLENOID
// =================================

#define SOLENOID_PIN 26

// MOSFET aktif ketika GPIO HIGH.
#define SOLENOID_ON  HIGH
#define SOLENOID_OFF LOW

// Durasi membuka pintu.
const unsigned long DURASI_BUKA = 3000;

// =================================
// UID KARTU YANG DIIZINKAN
// =================================

// Ganti dengan UID kartu milikmu.
// Contoh ini hanya UID dummy.
const char* UID_DIIZINKAN[] = {
  "A1B2C3D4"
};

const int JUMLAH_KARTU =
  sizeof(UID_DIIZINKAN) /
  sizeof(UID_DIIZINKAN[0]);

// =================================
// STATUS PINTU
// =================================

bool pintuTerbuka = false;

unsigned long waktuBuka = 0;

// =================================
// MEMBACA UID RFID
// =================================

String bacaUID() {

  String uid = "";

  for (byte i = 0; i < rfid.uid.size; i++) {

    if (rfid.uid.uidByte[i] < 0x10) {
      uid += "0";
    }

    uid += String(
      rfid.uid.uidByte[i],
      HEX
    );
  }

  uid.toUpperCase();

  return uid;
}

// =================================
// MEMERIKSA KARTU
// =================================

bool kartuDiizinkan(String uid) {

  for (int i = 0; i < JUMLAH_KARTU; i++) {

    if (uid.equalsIgnoreCase(
      UID_DIIZINKAN[i]
    )) {
      return true;
    }
  }

  return false;
}

// =================================
// MEMBUKA PINTU
// =================================

void bukaPintu() {

  digitalWrite(
    SOLENOID_PIN,
    SOLENOID_ON
  );

  pintuTerbuka = true;
  waktuBuka = millis();

  Serial.println(
    "[AKSES DITERIMA] Pintu dibuka."
  );
}

// =================================
// MENUTUP PINTU
// =================================

void tutupPintu() {

  digitalWrite(
    SOLENOID_PIN,
    SOLENOID_OFF
  );

  pintuTerbuka = false;

  Serial.println(
    "[INFO] Waktu akses berakhir."
  );
}

// =================================
// SETUP
// =================================

void setup() {

  Serial.begin(115200);

  pinMode(
    SOLENOID_PIN,
    OUTPUT
  );

  // Kondisi awal: solenoid tidak aktif.
  digitalWrite(
    SOLENOID_PIN,
    SOLENOID_OFF
  );

  SPI.begin(
    18,  // SCK
    19,  // MISO
    23,  // MOSI
    5    // SS
  );

  rfid.PCD_Init();

  Serial.println();
  Serial.println(
    "SMART DOOR LOCK - RFID"
  );

  Serial.println(
    "Tempelkan kartu RFID."
  );
}

// =================================
// LOOP
// =================================

void loop() {

  // Menutup kembali setelah durasi habis.
  if (
    pintuTerbuka &&
    millis() - waktuBuka >= DURASI_BUKA
  ) {

    tutupPintu();
  }

  // Tidak ada kartu baru.
  if (!rfid.PICC_IsNewCardPresent()) {
    return;
  }

  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }

  String uid = bacaUID();

  Serial.print("UID Kartu: ");
  Serial.println(uid);

  if (kartuDiizinkan(uid)) {

    bukaPintu();

  } else {

    Serial.println(
      "[AKSES DITOLAK] Kartu tidak terdaftar."
    );
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();

  delay(300);
}