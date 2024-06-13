# Privacy and Security

## Overview

Welcome to **LiveRecall**, an open-source alternative to Microsoft's Recall, designed with a strong emphasis on user privacy and data security. This document outlines our commitment to ensuring your data remains secure and private at all times.

## Privacy

### Local Execution

- **Local Processing:** LiveRecall operates entirely on your local machine. There is no mechanism for us to access your data or see how the software is being used.
- **No Remote Access:** All processing occurs offline after the initial download of dependencies. The application does not require internet access for its core functionalities.

### Data Security

- **Local Models:** All models and data used by LiveRecall are stored and run locally. This ensures that no data is transmitted over the internet.
- **Image Encryption:** All screenshots captured by LiveRecall are encrypted and stored locally.
  - **Encryption:** Images are encrypted using a simple password that you provide. This password is not stored and must be remembered by the user.
  - **Decryption for Retrieval:** Images are only decrypted temporarily when they are retrieved for viewing.
  - **Secure Deletion:** Once decrypted and used, the images are promptly deleted to prevent unauthorized access.

## Transparency

### Open Source

- **Community-Driven:** LiveRecall is fully open-source, ensuring transparency in how your data is handled. You are encouraged to review the codebase to understand the security measures implemented.
- **Contributions:** We welcome community contributions to improve the security and functionality of LiveRecall. Feel free to fork the repository and submit pull requests.

### Issue Reporting

- **Feedback:** If you have any questions, concerns, or suggestions regarding privacy and security, please create an issue on our GitHub repository. We are committed to addressing any issues and enhancing our security practices based on user feedback.

## Future Enhancements

- **Improved Encryption:** Enhanced encryption methods are being developed to further secure your data.
- **Database Support:** An option to add PostgreSQL support will be available soon, providing more robust data management while maintaining security.

## Contact

For any further inquiries or detailed information regarding privacy and security, please create an issue on our GitHub repository. We are dedicated to ensuring that your experience with LiveRecall is secure and private.

Thank you for using LiveRecall!

---

Enjoy using LiveRecall! If you like the project, please give it a star on GitHub.

[GitHub: VedankPurohit](https://github.com/VedankPurohit)