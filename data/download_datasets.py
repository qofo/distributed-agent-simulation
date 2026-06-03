import os
import json
from datasets import load_dataset

def main():
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    
    print("Downloading CNN-Dailymail (Task A)...")
    try:
        # Get a small sample from the test split
        cnn_dataset = load_dataset("cnn_dailymail", "3.0.0", split="test")
        cnn_sample = []
        for i in range(100):
            if i < len(cnn_dataset):
                cnn_sample.append({
                    "id": cnn_dataset[i]["id"],
                    "article": cnn_dataset[i]["article"],
                    "highlights": cnn_dataset[i]["highlights"]
                })
        
        with open(os.path.join(data_dir, "cnn_dailymail_sample.json"), "w", encoding="utf-8") as f:
            json.dump(cnn_sample, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(cnn_sample)} articles to cnn_dailymail_sample.json")
    except Exception as e:
        print(f"Failed to download CNN-Dailymail: {e}")

    print("Downloading HotpotQA (Task B)...")
    try:
        # Get a small sample from validation split
        hotpot_dataset = load_dataset("hotpot_qa", "distractor", split="validation")
        hotpot_sample = []
        for i in range(100):
            if i < len(hotpot_dataset):
                hotpot_sample.append({
                    "id": hotpot_dataset[i]["id"],
                    "question": hotpot_dataset[i]["question"],
                    "answer": hotpot_dataset[i]["answer"],
                    "type": hotpot_dataset[i]["type"],
                    "level": hotpot_dataset[i]["level"]
                })
                
        with open(os.path.join(data_dir, "hotpotqa_sample.json"), "w", encoding="utf-8") as f:
            json.dump(hotpot_sample, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(hotpot_sample)} questions to hotpotqa_sample.json")
    except Exception as e:
        print(f"Failed to download HotpotQA: {e}")

if __name__ == "__main__":
    main()
