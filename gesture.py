import cv2
import numpy as np
import copy
import math
#from appscript import app

# 環境:
# ハードウェア：Raspberry Pi 4B
# OS    : Raspbian GNU/Linux 10 (buster)
# Python: 3.7.3
# OpenCV: 4.2.0

# パラメータ
cap_region_x_begin=0.5  # 開始点/全体の幅
cap_region_y_end=0.8  # 終了点/全体の幅
threshold = 60  # 二値化のしきい値
blurValue = 41  # ガウシアンブラーのパラメータ
bgSubThreshold = 50
learningRate = 0

# 変数
isBgCaptured = 0   # 背景がキャプチャされたかどうかのフラグ
triggerSwitch = False  # Trueの場合、キーボードシミュレーターが動作する

def printThreshold(thr):
    print("! しきい値を " + str(thr) + " に変更しました")


def removeBG(frame):
    fgmask = bgModel.apply(frame,learningRate=learningRate)
    # カーネル = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    # res = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel)

    kernel = np.ones((3, 3), np.uint8)
    fgmask = cv2.erode(fgmask, kernel, iterations=1)
    res = cv2.bitwise_and(frame, frame, mask=fgmask)
    return res


def calculateFingers(res,drawing):  # -> 完了フラグ, 指の数を返す
    # 凸欠陥の計算
    hull = cv2.convexHull(res, returnPoints=False)
    if len(hull) > 3:
        defects = cv2.convexityDefects(res, hull)
        if type(defects) != type(None):  # クラッシュを防ぐため (バグ未発見)

            cnt = 0
            for i in range(defects.shape[0]):  # 角度を計算
                s, e, f, d = defects[i][0]
                start = tuple(res[s][0])
                end = tuple(res[e][0])
                far = tuple(res[f][0])
                a = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
                b = math.sqrt((far[0] - start[0]) ** 2 + (far[1] - start[1]) ** 2)
                c = math.sqrt((end[0] - far[0]) ** 2 + (end[1] - far[1]) ** 2)
                angle = math.acos((b ** 2 + c ** 2 - a ** 2) / (2 * b * c))  # 余弦定理
                if angle <= math.pi / 2:  # 角度が90度未満の場合、指と見なす
                    cnt += 1
                    cv2.line(drawing, far, start, [211, 200, 200], 2)
                    cv2.line(drawing, far, end, [211, 200, 200], 2)
                    cv2.circle(drawing, far, 8, [211, 84, 0], -1)
            return True, cnt
    return False, 0


# カメラ
camera = cv2.VideoCapture(0)
#rt = camera.get(10)
#print(rt)
camera.set(10,150)
cv2.namedWindow('trackbar')
cv2.createTrackbar('trh1', 'trackbar', threshold, 100, printThreshold)


while camera.isOpened():
    ret, frame = camera.read()
    threshold = cv2.getTrackbarPos('trh1', 'trackbar')
    frame = cv2.bilateralFilter(frame, 5, 50, 100)  # スムージングフィルター
    frame = cv2.flip(frame, 1)  # フレームを水平に反転
    cv2.rectangle(frame, (int(cap_region_x_begin * frame.shape[1]), 0),
                 (frame.shape[1], int(cap_region_y_end * frame.shape[0])), (255, 0, 0), 2)
    cv2.imshow('original', frame)

    # メイン操作
    if isBgCaptured == 1:  # 背景がキャプチャされるまでこの部分は実行されない
        img = removeBG(frame)
        img = img[0:int(cap_region_y_end * frame.shape[0]),
                    int(cap_region_x_begin * frame.shape[1]):frame.shape[1]]  # ROIを切り取る
        #cv2.imshow('mask', img)

        # 画像を二値化
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (blurValue, blurValue), 0)
        #cv2.imshow('blur', blur)
        ret, thresh = cv2.threshold(blur, threshold, 255, cv2.THRESH_BINARY)
        #cv2.imshow('ori', thresh)


        # 輪郭を取得
        thresh1 = copy.deepcopy(thresh)
        contours, hierarchy = cv2.findContours(thresh1, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        length = len(contours)
        maxArea = -1
        if length > 0:
            for i in range(length):  # 最大の輪郭を探す（面積による）
                temp = contours[i]
                area = cv2.contourArea(temp)
                if area > maxArea:
                    maxArea = area
                    ci = i

            res = contours[ci]
            #print(res)
            hull = cv2.convexHull(res)
            drawing = np.zeros(img.shape, np.uint8)
            #cv2.drawContours(drawing, [], 0, (0, 255, 0), 2)
            cv2.drawContours(drawing, [res], 0, (0, 255, 0), 2)
            cv2.drawContours(drawing, [hull], 0, (0, 0, 255), 3)

            isFinishCal,cnt = calculateFingers(res,drawing)
            if triggerSwitch is True:
                # isFinishCalがTrueでcntが2以下の場合
                if isFinishCal is True:
                    print (cnt)
                    #app('System Events').keystroke(' ')  # スペースキーをシミュレート
                    

        cv2.imshow('output', drawing)

    # キーボード操作
    k = cv2.waitKey(10)
    if k == 27:  # ESCキーで終了
        camera.release()
        cv2.destroyAllWindows()
        break
    elif k == ord('b'):  # 'b'を押すと背景をキャプチャ
        bgModel = cv2.createBackgroundSubtractorMOG2(0, bgSubThreshold)
        isBgCaptured = 1
        print('!!!背景キャプチャ完了!!!')
    elif k == ord('r'):  # 'r'を押すと背景をリセット
        bgModel = None
        triggerSwitch = False
        isBgCaptured = 0
        print('!!!背景リセット完了!!!')
    elif k == ord('n'):
        triggerSwitch = True
        print('!!!トリガーオン!!!')