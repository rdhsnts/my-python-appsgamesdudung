import cv2
import time
import os
import random
import math
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision
import tkinter as tk
from tkinter import simpledialog, messagebox

# ─── SYSTEM LOCK & PASSWORD CHECK ───────────────────────────────────────────
PASSWORD_BENAR = "1234"

def verifikasi_password():
    root = tk.Tk()
    root.withdraw()  # Sembunyikan window utama tkinter
    
    percobaan = 3
    while percobaan > 0:
        pwd = simpledialog.askstring("System Lock", "Masukkan Password Game:", show='*')
        if pwd == PASSWORD_BENAR:
            messagebox.showinfo("Berhasil", "Akses Diterima! Selamat Bermain.")
            root.destroy()
            return True
        elif pwd is None:  # Jika pengguna menekan Cancel
            break
        else:
            percobaan -= 1
            messagebox.showwarning("Gagal", f"Password Salah! Sisa percobaan: {percobaan}")
            
    root.destroy()
    return False

if not verifikasi_password():
    raise SystemExit

# ─── KONFIGURASI UMUM & MEDIAPIPE ───────────────────────────────────────────
MODEL = "hand_landmarker.task"
SUMBER = 0  # Webcam
LEBAR, TINGGI = 960, 540

FONT = cv2.FONT_HERSHEY_DUPLEX
CYAN = (255, 235, 0)
MAGENTA = (200, 0, 255)
PUTIH = (240, 245, 250)
HIJAU = (80, 220, 100)
MERAH = (80, 80, 220)
KUNING = (0, 215, 255)
ABU = (100, 100, 100)

cap = cv2.VideoCapture(SUMBER)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, LEBAR)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TINGGI)

if not cap.isOpened():
    print("Kamera gagal dibuka.")
    raise SystemExit

opsi = vision.HandLandmarkerOptions(
    base_options=mp.tasks.BaseOptions(model_asset_path=MODEL),
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)
landmarker = vision.HandLandmarker.create_from_options(opsi)

cv2.namedWindow("Hand Tracking Game Hub", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Hand Tracking Game Hub", LEBAR, TINGGI)

# ─── STATE MANAGEMENT ──────────────────────────────────────────────────────
mode_aplikasi = "MENU"  # "MENU", "GAME_TANGKAP", "GAME_TICTACTOE"

# State Game 1: Tangkap Objek
skor_tangkap = 0
nyawa_tangkap = 5
game_over_tangkap = False
target_x = random.randint(50, LEBAR - 50)
target_y = 0
target_speed = 7
target_radius = 20

# State Game 2: Tic Tac Toe
board = [""] * 9  # 3x3 grid
turn = "X"        # "X" = Player, "O" = Bot
pemenang_ttt = None
waktu_tahan_fist = 0

ts = 0
prev_time = 0

# ─── HELPER FUNCTIONS ────────────────────────────────────────────────────────
def teks(img, s, org, skala, tebal=2, warna=PUTIH):
    cv2.putText(img, s, org, FONT, skala, warna, tebal, cv2.LINE_AA)

def is_kepal(hand):
    # Cek apakah semua ujung jari tertekuk mendekati pergelangan
    w = hand[0]
    d_jari = [math.hypot(hand[i].x - w.x, hand[i].y - w.y) for i in [8, 12, 16, 20]]
    ref = math.hypot(hand[5].x - w.x, hand[5].y - w.y)
    return all(d < ref * 1.1 for d in d_jari)

def reset_tangkap():
    global skor_tangkap, nyawa_tangkap, game_over_tangkap, target_y, target_speed, target_x
    skor_tangkap = 0
    nyawa_tangkap = 5
    game_over_tangkap = False
    target_y = 0
    target_speed = 7
    target_x = random.randint(50, LEBAR - 50)

def reset_ttt():
    global board, turn, pemenang_ttt
    board = [""] * 9
    turn = "X"
    pemenang_ttt = None

def cek_menang_ttt(b):
    pola = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
    for p1, p2, p3 in pola:
        if b[p1] == b[p2] == b[p3] and b[p1] != "":
            return b[p1]
    if "" not in b:
        return "SERI"
    return None

def bot_move():
    global board, turn, pemenang_ttt
    kosong = [i for i, v in enumerate(board) if v == ""]
    if kosong and pemenang_ttt is None:
        pilihan = random.choice(kosong)
        board[pilihan] = "O"
        pemenang_ttt = cek_menang_ttt(board)
        turn = "X"

# ─── LOOP UTAMA ──────────────────────────────────────────────────────────────
while True:
    ok, frame = cap.read()
    if not ok:
        break

    frame = cv2.flip(frame, 1)
    frame = cv2.resize(frame, (LEBAR, TINGGI))
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    ts += 1
    hasil = landmarker.detect_for_video(
        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts * 33)
    
    pos_tangan = None
    tangan_dikepal = False
    if hasil.hand_landmarks:
        hand = hasil.hand_landmarks[0]
        px = int(hand[8].x * LEBAR)
        py = int(hand[8].y * TINGGI)
        pos_tangan = (px, py)
        tangan_dikepal = is_kepal(hand)

    # -------------------------------------------------------------------------
    # MODE 1: MENU UTAMA
    # -------------------------------------------------------------------------
    if mode_aplikasi == "MENU":
        cv2.rectangle(frame, (0, 0), (LEBAR, TINGGI), (30, 20, 40), cv2.FILLED)
        teks(frame, "SELECT GAME HUB", (LEBAR // 2 - 180, 80), 1.2, 3, CYAN)
        
        # Tombol 1: Game Tangkap Objek
        box1 = (100, 180, 420, 380)
        cv2.rectangle(frame, (box1[0], box1[1]), (box1[2], box1[3]), HIJAU, 3)
        teks(frame, "1. TANGKAP OBJEK", (box1[0] + 20, box1[1] + 100), 0.7, 2, PUTIH)
        
        # Tombol 2: Game Tic Tac Toe
        box2 = (540, 180, 860, 380)
        cv2.rectangle(frame, (box2[0], box2[1]), (box2[2], box2[3]), MAGENTA, 3)
        teks(frame, "2. TIC TAC TOE", (box2[0] + 30, box2[1] + 100), 0.7, 2, PUTIH)

        if pos_tangan:
            cv2.circle(frame, pos_tangan, 15, KUNING, cv2.FILLED)
            tx, ty = pos_tangan
            
            # Cek Pilihan Menu
            if box1[0] < tx < box1[2] and box1[1] < ty < box1[3]:
                cv2.rectangle(frame, (box1[0], box1[1]), (box1[2], box1[3]), KUNING, cv2.FILLED)
                teks(frame, "MEMBUKA...", (box1[0] + 80, box1[1] + 100), 0.8, 2, (0,0,0))
                reset_tangkap()
                mode_aplikasi = "GAME_TANGKAP"
                
            elif box2[0] < tx < box2[2] and box2[1] < ty < box2[3]:
                cv2.rectangle(frame, (box2[0], box2[1]), (box2[2], box2[3]), KUNING, cv2.FILLED)
                teks(frame, "MEMBUKA...", (box2[0] + 80, box2[1] + 100), 0.8, 2, (0,0,0))
                reset_ttt()
                mode_aplikasi = "GAME_TICTACTOE"

        teks(frame, "Arahkan Telunjuk ke Kotak untuk Memilih", (LEBAR // 2 - 200, 480), 0.6, 1, PUTIH)

    # -------------------------------------------------------------------------
    # MODE 2: GAME TANGKAP OBJEK
    # -------------------------------------------------------------------------
    elif mode_aplikasi == "GAME_TANGKAP":
        if not game_over_tangkap:
            target_y += target_speed

            if target_y > TINGGI:
                nyawa_tangkap -= 1
                target_y = 0
                target_x = random.randint(50, LEBAR - 50)
                if nyawa_tangkap <= 0:
                    game_over_tangkap = True

            if pos_tangan:
                jarak = math.hypot(pos_tangan[0] - target_x, pos_tangan[1] - target_y)
                if jarak < (target_radius + 25):
                    skor_tangkap += 10
                    target_y = 0
                    target_x = random.randint(50, LEBAR - 50)
                    target_speed = 7 + (skor_tangkap // 30)

            cv2.circle(frame, (target_x, target_y), target_radius, MERAH, cv2.FILLED)
            cv2.circle(frame, (target_x, target_y), target_radius, PUTIH, 2)

            if pos_tangan:
                cv2.circle(frame, pos_tangan, 25, HIJAU, cv2.FILLED)
                cv2.circle(frame, pos_tangan, 30, KUNING, 2)
        else:
            cv2.rectangle(frame, (LEBAR // 4, TINGGI // 4), (3 * LEBAR // 4, 3 * TINGGI // 4), (0, 0, 0), cv2.FILLED)
            teks(frame, "GAME OVER", (LEBAR // 2 - 130, TINGGI // 2 - 20), 1.2, 3, MERAH)
            teks(frame, f"Skor Akhir: {skor_tangkap}", (LEBAR // 2 - 80, TINGGI // 2 + 30), 0.8, 2, KUNING)
            teks(frame, "Tekan 'R' untuk Reset | 'M' ke Menu", (LEBAR // 2 - 180, TINGGI // 2 + 70), 0.5, 1, PUTIH)

        teks(frame, f"SKOR: {skor_tangkap}", (20, 40), 0.8, 2, CYAN)
        teks(frame, f"NYAWA: {nyawa_tangkap}", (20, 80), 0.8, 2, MERAH if nyawa_tangkap <= 2 else HIJAU)

    # -------------------------------------------------------------------------
    # MODE 3: GAME TIC TAC TOE
    # -------------------------------------------------------------------------
    elif mode_aplikasi == "GAME_TICTACTOE":
        # Render Board 3x3
        offset_x, offset_y = 280, 70
        cell_size = 130

        for row in range(3):
            for col in range(3):
                idx = row * 3 + col
                x1 = offset_x + col * cell_size
                y1 = offset_y + row * cell_size
                x2, y2 = x1 + cell_size, y1 + cell_size

                cv2.rectangle(frame, (x1, y1), (x2, y2), PUTIH, 2)
                
                # Render simbol X dan O
                if board[idx] == "X":
                    cv2.line(frame, (x1 + 20, y1 + 20), (x2 - 20, y2 - 20), CYAN, 4)
                    cv2.line(frame, (x1 + 20, y2 - 20), (x2 - 20, y1 + 20), CYAN, 4)
                elif board[idx] == "O":
                    cv2.circle(frame, (x1 + cell_size // 2, y1 + cell_size // 2), 40, MAGENTA, 4)

                # Deteksi Tangan Memilih Kotak
                if pos_tangan and turn == "X" and pemenang_ttt is None:
                    tx, ty = pos_tangan
                    if x1 < tx < x2 and y1 < ty < y2 and board[idx] == "":
                        cv2.rectangle(frame, (x1, y1), (x2, y2), KUNING, 3)
                        
                        # Kepal tangan untuk konfirmasi memilih kotak
                        if tangan_dikepal:
                            board[idx] = "X"
                            pemenang_ttt = cek_menang_ttt(board)
                            turn = "O"
                            if pemenang_ttt is None:
                                bot_move()

        # Visualisasi Status Permainan
        if pemenang_ttt:
            txt = "SERI!" if pemenang_ttt == "SERI" else f"PEMENANG: {pemenang_ttt}"
            teks(frame, txt, (LEBAR // 2 - 120, TINGGI - 50), 1.0, 3, KUNING)
            teks(frame, "Tekan 'R' untuk Reset | 'M' ke Menu", (20, TINGGI - 20), 0.5, 1, PUTIH)
        else:
            teks(frame, "Kepal Tangan (Fist) untuk Pilih Kotak", (LEBAR // 2 - 200, TINGGI - 20), 0.6, 1, PUTIH)

        if pos_tangan:
            warna_p = MERAH if tangan_dikepal else HIJAU
            cv2.circle(frame, pos_tangan, 12, warna_p, cv2.FILLED)

    # ─── HUD ATAS / COMMON ───────────────────────────────────────────────────
    teks(frame, "[M] Menu Utama | [Q] Keluar", (LEBAR - 320, 30), 0.5, 1, ABU)

    now = time.time()
    fps = 1 / (now - prev_time) if prev_time else 0
    prev_time = now
    teks(frame, f"FPS: {int(fps)}", (20, TINGGI - 20) if mode_aplikasi != "GAME_TICTACTOE" else (LEBAR - 100, TINGGI - 20), 0.5, 1, PUTIH)

    cv2.imshow("Hand Tracking Game Hub", frame)

    # ─── KONTROL KEYBOARD ────────────────────────────────────────────────────
    k = cv2.waitKey(1) & 0xFF
    if k == ord('q'):
        break
    elif k == ord('m'):
        mode_aplikasi = "MENU"
    elif k == ord('r'):
        if mode_aplikasi == "GAME_TANGKAP":
            reset_tangkap()
        elif mode_aplikasi == "GAME_TICTACTOE":
            reset_ttt()

cap.release()
cv2.destroyAllWindows()
landmarker.close()