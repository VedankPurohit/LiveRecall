import os

def ListFiles(directory_path):
    try:
        items = os.listdir(directory_path)
        
        files = [os.path.join(directory_path, item) for item in items if os.path.isfile(os.path.join(directory_path, item))]
        
        return files
    except Exception as e:
        return f"An error occurred: {e}"

def EncryptDecryptImage(image_path, key, save_path= ""):
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

def main():
    print("Welcome to Image Encryption and Decryption!")
    directory_path = input("Enter the directory path: ")
    key = input("Enter the encryption key: ")
    files = ListFiles(directory_path)
    print(files)
    for a in files:
        EncryptDecryptImage(a, key)

if __name__ == "__main__":
    main()
