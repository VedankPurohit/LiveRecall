import os
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

def ListFiles(directory_path):
    try:
        items = os.listdir(directory_path)
        
        files = [os.path.join(directory_path, item) for item in items if os.path.isfile(os.path.join(directory_path, item))]
        
        return files
    except Exception as e:
        return f"An error occurred: {e}"

def EncryptDecryptImage(image_path, key, save_path= ""):
    if key == "DevMode": # For testing purposes, No encription will be done, the image will be saved as is DO NOT USE FOR NORMAL USAGE
        if save_path == "":
            save_path = image_path
        print("DevMode Activated, No Security")
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
        with open(save_path, 'wb') as image_file:
            image_file.write(image_data)
    else: #Normal Workings
        if save_path == "":
            save_path = image_path
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()

        if isinstance(key, str):
            key = key.encode()

        encrypted_data = bytearray()
        for i in range(len(image_data)):
            encrypted_data.append(image_data[i] ^ key[i % len(key)])

        with open(save_path, 'wb') as image_file:
            image_file.write(encrypted_data)


def process_image(file, key):
    EncryptDecryptImage(file, key)
    return file

def main():
    print("Welcome to Image Encryption and Decryption!")
    directory_path = input("Enter the directory path: ")
    if directory_path == "":
        directory_path = "CapturedData"
    print(directory_path)
    key = input("Enter the encryption key: ")
    print(len(key))
    files = ListFiles(directory_path)
    total_files = len(files)

    if total_files == 0:
        print("No files to process.")
        return
    
    print(f"{total_files} Total files")

    # Use min() to ensure that we don't use more threads than there are files
    max_workers = min(16, total_files)  # 8 is an example; adjust based on CPU cores

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_image, file, key) for file in files]

        with tqdm(total=total_files, desc="Processing Files", bar_format="{l_bar}{bar} | {n_fmt}/{total_fmt} files | {rate_fmt} | time left: {remaining}") as pbar:
            for future in as_completed(futures):
                pbar.update(1)
    
    print(f"Converted {total_files} Files")






if __name__ == "__main__":
    main()

