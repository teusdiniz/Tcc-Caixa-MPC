# 📦 Caixa de Ferramentas Automatizada com Visão Computacional e NFC
# 📦 Automated Toolbox with Computer Vision and NFC

---

## 🇧🇷 Português

### 📌 Visão Geral

Este projeto foi desenvolvido como **Trabalho de Conclusão de Curso (TCC)** e tem como objetivo a criação de uma **caixa de ferramentas automatizada e inteligente**, integrando **hardware**, **software**, **visão computacional** e **comunicação IoT**.

O sistema realiza o controle completo de **retirada e devolução de ferramentas**, utilizando **autenticação por cartão NFC**, **gavetas automatizadas**, **processamento de imagem para validação** e **registro de todas as operações em banco de dados**.

---

### 🎯 Objetivo do Projeto

Desenvolver uma solução capaz de:

- Identificar usuários por meio de **NFC/RFID**
- Controlar automaticamente a abertura e o fechamento de gavetas
- Permitir a retirada e devolução controlada de ferramentas
- Validar as operações por **visão computacional**
- Registrar histórico completo (usuário, ferramenta, data, hora e imagem)
- Reduzir perdas, extravios e falhas humanas no controle de ferramentas

---

### 🧠 Arquitetura do Sistema

O sistema é dividido em três camadas principais:

#### 1. Hardware (IoT / Edge)
- Rock Pi 4
- Leitor NFC RC522
- Atuadores para abertura e fechamento das gavetas
- LEDs auxiliares para iluminação
- Comunicação via **MQTT**

#### 2. Servidor (PC interno da caixa)
- Back-end desenvolvido em **Python com Django**
- Banco de dados **MySQL**
- Processamento de imagem com **OpenCV**
- Servidor Web responsável pela interface do usuário

#### 3. Interface Web
- Autenticação do usuário
- Seleção de retirada ou devolução
- Escolha das ferramentas
- Confirmação das operações
- Retorno automático ao estado inicial

---

### 🔄 Fluxo de Funcionamento

#### 🔐 Autenticação
1. O usuário aproxima o cartão NFC do leitor.
2. A Rock Pi 4 envia o UID via MQTT para o servidor.
3. O servidor valida o usuário no banco de dados.
4. Caso autorizado, o acesso ao sistema é liberado.

#### 🧰 Retirada de Ferramentas
- Seleção das ferramentas disponíveis
- Registro da retirada no banco de dados
- Abertura automática da(s) gaveta(s) correspondente(s)
- Acionamento do LED para melhor iluminação
- Captura de imagem da gaveta
- Validação da retirada por visão computacional
- Salvamento da imagem como evidência
- Fechamento automático da gaveta

#### 🔁 Devolução de Ferramentas
- Listagem das ferramentas vinculadas ao usuário
- Seleção das ferramentas a serem devolvidas
- Abertura da gaveta correspondente
- Captura de imagem e validação por processamento de imagem
- Registro da devolução no banco de dados
- Fechamento automático da gaveta

---

### 🖼️ Processamento de Imagem e Visão Computacional

O projeto utiliza **OpenCV** para validar automaticamente as operações realizadas na caixa.

A validação é feita por meio da comparação entre:
- A imagem atual da gaveta
- Uma imagem de referência previamente cadastrada

Principais módulos:
- `gaveta_detect.py`: responsável pela detecção e validação das ferramentas
- `roi_picker.py`: definição das regiões de interesse (ROIs) de cada gaveta

Esse processo garante maior confiabilidade e rastreabilidade das operações.

---

### 🗄️ Modelagem do Banco de Dados

Principais entidades do sistema:

- **Usuário**
  - UID
  - Nome
  - CPF
  - Data de nascimento
  - Cargo

- **Ferramenta**
  - Nome
  - Gaveta
  - Baia
  - Status

- **Movimentação**
  - Tipo (retirada/devolução)
  - Usuário
  - Ferramenta
  - Data e hora
  - Imagem de registro

---

### 🔌 Comunicação MQTT

A comunicação entre a Rock Pi 4 e o servidor é realizada via **MQTT**, sendo utilizada para:

- Envio do UID do cartão NFC
- Comandos de abertura e fechamento das gavetas
- Acionamento de LEDs
- Sincronização entre hardware e servidor

---

### 🛠️ Tecnologias Utilizadas

- Python  
- Django  
- OpenCV  
- MQTT  
- MySQL  
- HTML, CSS e JavaScript  
- Rock Pi 4  
- Leitor NFC RC522  
- Câmera USB industrial  

---

### 📁 Estrutura do Projeto

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

### 📸 Imagens do Projeto

As imagens abaixo ilustram a estrutura física da caixa, a interface web do sistema e o processamento de imagem utilizado para validação das operações.

<p align="center">
  <img src="docs/images/caixa_externa.jpg" width="45%" />
  <img src="docs/images/caixa_interna.jpg" width="45%" />
</p>

<p align="center">
  <img src="docs/images/gavetas_abertas.jpg" width="60%" />
</p>

<p align="center">
  <img src="docs/images/tela_inicial.png" width="45%" />
  <img src="docs/images/tela_retirada.png" width="45%" />
</p>

<p align="center">
  <img src="docs/images/processamento_resultado.png" width="60%" />
</p>

---

### 📌 Considerações Finais

Este projeto demonstra a aplicação prática de **IoT**, **automação**, **engenharia de software** e **visão computacional**, podendo ser facilmente adaptado para ambientes industriais e sistemas de controle de inventário em larga escala.

---

## 🇺🇸 English

### 📌 Overview

This project was developed as a **Final Graduation Project (TCC)** and focuses on building an **automated and intelligent toolbox**, integrating **hardware**, **software**, **computer vision**, and **IoT communication**.

The system controls **tool withdrawal and return** using **NFC authentication**, **automated drawers**, **computer vision validation**, and **full operation logging in a database**.

---

### 🎯 Project Objective

To develop a solution capable of:

- Identifying users via **NFC/RFID**
- Automatically controlling drawer opening and closing
- Managing tool withdrawal and return
- Validating operations using **computer vision**
- Storing complete operation history
- Reducing losses and human errors

---

### 🧠 System Architecture

The system is divided into three main layers:

#### 1. Hardware (IoT / Edge)
- Rock Pi 4
- RC522 NFC reader
- Drawer actuators
- Auxiliary LEDs
- **MQTT** communication

#### 2. Server (Internal PC)
- Back-end developed with **Python and Django**
- **MySQL** database
- Image processing using **OpenCV**
- Web server for the user interface

#### 3. Web Interface
- User authentication
- Withdrawal and return selection
- Tool selection
- Operation confirmation

---

### 🔄 Operation Flow

- NFC authentication
- Tool selection
- Automatic drawer control
- Image capture and validation
- Database logging
- Automatic system reset

---

### 🖼️ Computer Vision

Computer vision is used to validate operations by comparing the current drawer image with a reference image.

Main modules:
- `gaveta_detect.py`
- `roi_picker.py`

---

### 🛠️ Technologies Used

- Python  
- Django  
- OpenCV  
- MQTT  
- MySQL  
- HTML, CSS, JavaScript  
- Rock Pi 4  
- RC522 NFC reader  
- Industrial USB camera  

---

### 📌 Final Notes

This project represents a real-world application of **automation**, **IoT**, **computer vision**, a
