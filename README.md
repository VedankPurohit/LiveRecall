# LiveRecall

Welcome to **LiveRecall**, the open-source alternative to Microsoft's Recall. LiveRecall captures snapshots of your screen and allows you to recall them using natural language queries, leveraging semantic search technology. For added security, all images are encrypted.

Get an idea of what Microsoft Recall is -
[Tweet](https://x.com/elonmusk/status/1792690964672450971?t=LeVxPsxW0VopuLltIBfWdA&s=19) 

## Overview

### What Does LiveRecall Do?

LiveRecall is designed to help you easily find and recall specific moments you’ve seen on your screen. Imagine these scenarios:

- You saw a blue shirt online but can’t remember where.
- You received a meme or message but can’t recall who sent it or on which platform.

![LiveRecall Infrance](Images/Screenshot%202024-06-13%20083549.png)

LiveRecall addresses these needs by capturing screenshots whenever a change is detected on your screen and at regular intervals. This data is then used for recall, allowing you to describe what you’re looking for in natural language, and the appropriate image will be shown.

## Features

- **Open Source**: Fully transparent and community-driven development.
- **Semantic Search**: Retrieve your snapshots using simple natural language descriptions.
- **Continuous Capture**: Takes screenshots when changes are detected and at specified intervals.
- **Encryption**: Ensures your screenshots are securely stored with simple encryption (enhanced encryption is on the way).

## Getting Started

### Prerequisites

Ensure you have the following installed on your machine:

- [Git](https://git-scm.com/downloads)
  or just download this as a zip from above green button

Note- There are bugs and persofamace issues which will be solved alongside a good GUI.
The Decision to not add a databse was done to remove friction. an oprtion to add Postgree will be added soon

### Installation

1. **Clone the repository or download the code directly:**

   ```bash
   git clone https://github.com/VedankPurohit/LiveRecall.git
   ```

2. **Navigate to the project directory:**

   ```bash
   cd LiveRecall
   ```

3. **Run the setup script (only required the first time):**

   On Windows:

   ```bash
   setup.bat
   ```

   This process will take some time as it sets up the necessary environment and dependencies.

4. **Launch the application:**

   On Windows:

   ```bash
   run.bat
   ```

   The duration depends on your internet connection as all required models will be downloaded.

5. **Access the web interface:**

   After running `run.bat`, a URL will be displayed. Click on the URL to open the web interface. Once everything is loaded, you will see a screen similar to this:

   ![LiveRecall Interface](Images/Screenshot%202024-06-13%20082741.png)


6. **Encryption Password:**

   - Enter a simple password for encryption and decryption.
     ![LiveRecall Password](Images/Screenshot%202024-06-13%20082759.png)

   - **Important**: This password is not stored for security reasons, so make sure to remember it.
   - An enhanced encryption method is coming soon.

7. **Start and Stop Capture:**

   - Click **Start** to begin capturing snapshots.
   - Click **Stop** to stop capturing and save the data.

8. **Search Snapshots:**

   Use the search bar to retrieve your screenshots using natural language queries.


## Privacy and Security

For detailed information on privacy and security of this project, please refer to the [Privacy and Security](https://github.com/VedankPurohit/LiveRecall/blob/main/Privacy%20and%20Security.md) document.

## Upcoming Features

- Proper Database Support
- Performace Improvement
- Snapshot Timeline
- Optimized Storage
- Improved Encryption
- Better GUI
- And more...

## Contributing

We welcome contributions from the community! If you'd like to contribute, please fork the repository and create a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

If you have any questions, feel free to reach out:

- GitHub: [VedankPurohit](https://github.com/VedankPurohit)

Enjoy using LiveRecall!
And if you like it, give it an star
