# Multi-User Text Editor

A real-time collaborative text editor that allows multiple users to edit documents simultaneously, similar to Google Docs.

## Features

- Real-time collaborative editing
- Multiple document support
- User presence awareness
- Simple and intuitive GUI
- Line-based synchronization
- Automatic conflict resolution

## Requirements

- Python 3.6 or higher
- Tkinter (included with Python)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/multi-user-word-editor.git
cd multi-user-word-editor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the server:
```bash
python server/server.py
```

2. Start one or more clients:
```bash
python client/client.py
```

3. In each client:
   - Enter a username to login
   - Create a new file or join an existing one
   - Start editing!

## Protocol

The application uses a simple text-based protocol for communication between clients and server. All messages follow the format: `HEADER:content`

### Message Types

#### Client to Server
- `LOGIN:username` - Login with username
- `FILE_CREATE:filename` - Create a new file
- `FILE_JOIN:filename` - Join an existing file
- `FILE_UPDATE:filename:line_number\ncontent` - Update file content
- `QUIT:username` - Disconnect from server

#### Server to Client
- `USER_LIST:user1,user2,...` - List of connected users
- `FILE_LIST:file1,file2,...` - List of available files
- `FILE_SYNC:filename\ncontent` - Full file content
- `FILE_UPDATE:filename:line_number\ncontent` - File update
- `ERROR:message` - Error message

## Architecture

The application follows a client-server architecture:

- **Server**: Manages user connections, file content, and broadcasts updates
- **Client**: Provides GUI and handles user interactions
- **Protocol**: Defines message formats and communication rules

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.