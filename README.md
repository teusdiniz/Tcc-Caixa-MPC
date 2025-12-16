# 📦 Automated Toolbox with Computer Vision and NFC
# 📦 Caixa de Ferramentas Automatizada com Visão Computacional e NFC

> Smart toolbox system using NFC authentication, automated drawers, computer vision validation, and IoT communication via MQTT.

---

## 📑 Table of Contents
- Overview
- Features
- System Architecture
- Tech Stack
- Libraries & Dependencies
- Project Structure
- Installation
- Usage Guide
- Computer Vision
- MQTT Communication
- Database Model
- Future Improvements
- License

---

## 🌍 Overview

### 🇺🇸 English

This project implements an **automated and intelligent toolbox** designed to manage **tool withdrawal and return** using **NFC authentication**, **motorized drawers**, and **computer vision validation**.

The system integrates **hardware (Rock Pi 4)**, **backend services (Django)**, **image processing (OpenCV)**, and **IoT communication (MQTT)** to ensure **traceability, security, and automation**.

Originally developed as a **Final Graduation Project (TCC)**, the architecture is suitable for **industrial and inventory-control environments**.

---

### 🇧🇷 Português

Este projeto implementa uma **caixa de ferramentas automatizada e inteligente**, projetada para controlar a **retirada e devolução de ferramentas** por meio de **autenticação NFC**, **gavetas motorizadas** e **validação por visão computacional**.

O sistema integra **hardware (Rock Pi 4)**, **back-end em Django**, **processamento de imagem com OpenCV** e **comunicação IoT via MQTT**, garantindo **rastreabilidade, segurança e automação**.

---

## ✨ Features

- NFC/RFID user authentication
- Automated drawer opening and closing
- Tool withdrawal and return workflow
- Computer vision-based validation
- Image evidence storage
- MQTT-based hardware communication
- Web-based user interface
- Full operation logging

---

## 🧠 System Architecture

**High-level architecture:**

- **Edge Device (Rock Pi 4)**
  - NFC reader (RC522)
  - Drawer actuators
  - LEDs
  - MQTT client

- **Server (Internal PC)**
  - Django backend
  - MySQL database
  - OpenCV image processing
  - MQTT broker/client
  - Web server

- **Web Interface**
  - User authentication
  - Operation selection
  - Tool selection and confirmation

---

## 🛠️ Tech Stack

### Backend
- Python 3.9+
- Django
- Django REST Framework

### Computer Vision
- OpenCV
- NumPy
- scikit-image

### Communication
- MQTT
- paho-mqtt

### Database
- MySQL
- mysqlclient / mysql-connector-python

### Frontend
- HTML5
- CSS3
- JavaScript

### Hardware
- Rock Pi 4
- RC522 NFC reader
- Industrial USB camera
- Motorized drawers

---

## 📚 Libraries & Dependencies

Main Python dependencies used in the project:

django
djangorestframework
opencv-python
numpy
scikit-image
pillow
requests
paho-mqtt
mysqlclient

yaml
Copiar código

---

## 📁 Project Structure

/
├── backend/
│ ├── inventario/
│ ├── operacoes/
│ ├── mqtt/
│ └── manage.py
├── processamento_imagem/
│ ├── gaveta_detect.py
│ ├── roi_picker.py
│ └── referencias/
├── frontend/
│ └── web/
├── database/
│ └── schema.sql
├── docs/
│ └── images/
└── README.md

yaml
Copiar código

---

## ⚙️ Installation

### Requirements
- Python 3.9+
- MySQL Server
- MQTT Broker (Mosquitto recommended)
- USB Camera
- Rock Pi 4 (edge device)

### Backend Setup

```bash
git clone https://github.com/your-user/your-repo.git
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
▶️ Usage Guide
1. System Startup
Power on the Rock Pi 4 and server PC

Start the MQTT broker

Run the Django server

2. User Authentication
Scan NFC card on the reader

UID is sent via MQTT

User is validated in the database

3. Tool Withdrawal
Select Withdraw

Choose available tools

Confirm operation

Drawer opens automatically

System captures image and validates withdrawal

Drawer closes

4. Tool Return
Select Return

Choose tools linked to the user

Drawer opens

System validates return via image processing

Operation is logged

🖼️ Computer Vision
Tool validation is performed using image comparison techniques:

Each drawer has a reference image

Regions of Interest (ROIs) are predefined

Current image is compared with reference

Differences indicate tool movement

Main Scripts
gaveta_detect.py – tool detection and validation

roi_picker.py – ROI configuration per drawer

🔌 MQTT Communication
MQTT is used for asynchronous communication between the server and Rock Pi 4:

NFC UID transmission

Drawer control commands

LED activation

Operation synchronization

🗄️ Database Model
Main entities:

User

Tool

Movement (withdraw / return)

Each movement stores:

User

Tool

Timestamp

Operation type

Image evidence

🚀 Future Improvements
User roles and permissions

Real-time dashboard

Mobile-friendly interface

Machine learning-based tool classification

Cloud synchronization

Offline-first mode

📄 License
This project was developed for academic purposes and can be adapted for industrial or
