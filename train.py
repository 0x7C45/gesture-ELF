from ultralytics import YOLO
import torch

def main():
    torch.cuda.empty_cache()

    a1 = YOLO('best.pt')
    a1.train(
        data='hand.yaml',
        epochs=200,
        imgsz=640,       # 改小
        batch=8,         # 改小
        workers=0,       # 关闭多进程
        device=0
    )
    print('模型训练完毕')

if __name__ == '__main__':
    main()





yolo detect train data=F:/YOLOTRAIN/Hand.yaml model=F:/YOLOTRAIN/best.pt project=F:/YOLOTRAIN/output name=train24_batch8 imgsz=640 batch=8 epochs=300 device=0 lr0=0.005 cos_lr=True warmup_epochs=5 workers=4
