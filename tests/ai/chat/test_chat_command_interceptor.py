import pytest
import json
import os
from unittest.mock import MagicMock, patch, call, mock_open, ANY

# Since the class is in a sibling module, we need to adjust the python path for imports
# This is a common pattern in testing.
from ai.chat.chat_command_interceptor import ChatCommandInterceptor
from ai.chat.chat import Chat

@pytest.fixture
def mock_chat():
    """Fixture to create a mock Chat object."""
    chat = MagicMock(spec=Chat)
    chat.messages = []
    chat.EVENT_COMMAND_STARTED = "command_started"
    return chat

@pytest.fixture
def interceptor(mock_chat, tmp_path):
    """Fixture to create a ChatCommandInterceptor instance for each test."""
    # Use tmp_path for a temporary, isolated root folder for session files
    return ChatCommandInterceptor(chat=mock_chat, root_folder=str(tmp_path))

# Patch where the objects are looked up, which is inside the chat_command_interceptor module.
@patch('ai.chat.chat_command_interceptor.func')
class TestChatCommandInterceptor:

    def test_initialization(self, mock_func, mock_chat, tmp_path):
        """Tests that the interceptor registers its run method for the correct event."""
        interceptor_instance = ChatCommandInterceptor(chat=mock_chat, root_folder=str(tmp_path))
        
        mock_chat.add_event.assert_called_once_with(
            interceptor_instance.chat.EVENT_COMMAND_STARTED, 
            interceptor_instance.run
        )
        assert interceptor_instance.root_folder == str(tmp_path)
        assert interceptor_instance.extra_commands == []

    def test_run_invalid_command(self, mock_func, interceptor, mock_chat):
        """Tests that an invalid command prints an error and terminates."""
        command_text = "/invalid_command"
        interceptor.run(command_text)
        
        mock_func.out.assert_called_once_with("Invalid Command")
        mock_chat.terminate_command.assert_called_once()

    def test_run_delegates_to_save_session(self, mock_func, interceptor, mock_chat):
        """Tests if `/save` command correctly calls save_session."""
        with patch.object(interceptor, 'save_session') as mock_save:
            command_text = "/save my_session"
            interceptor.run(command_text)
            
            mock_save.assert_called_once_with("my_session")
            mock_chat.terminate_command.assert_called_once()

    def test_run_delegates_to_load_session(self, mock_func, interceptor, mock_chat):
        """Tests if `/load` command correctly calls load_session."""
        with patch.object(interceptor, 'load_session') as mock_load:
            command_text = "/load another_session"
            interceptor.run(command_text)
            
            mock_load.assert_called_once_with("another_session")
            mock_chat.terminate_command.assert_called_once()

    def test_run_delegates_to_list_sessions(self, mock_func, interceptor, mock_chat):
        """Tests if `/list` command correctly calls list_sessions."""
        with patch.object(interceptor, 'list_sessions') as mock_list:
            command_text = "/list"
            interceptor.run(command_text)
            
            mock_list.assert_called_once()
            mock_chat.terminate_command.assert_called_once()

    def test_run_command_without_argument_raises_error(self, mock_func, interceptor, mock_chat):
        """Tests that commands requiring an argument raise an error if not provided."""
        with pytest.raises(IndexError):
            interceptor.run("/save")
        # The command should not be terminated because the exception happens before
        mock_chat.terminate_command.assert_not_called()

        # Reset mock for next assertion
        mock_chat.reset_mock()

        with pytest.raises(IndexError):
            interceptor.run("/load")
        mock_chat.terminate_command.assert_not_called()

    def test_run_extra_command_raises_error(self, mock_func, interceptor, mock_chat):
        """Tests that the extra_command branch raises an AttributeError due to a missing method."""
        interceptor.extra_commands = ['/extra']
        with pytest.raises(AttributeError, match="'ChatCommandInterceptor' object has no attribute 'handled_extra_command'"):
            interceptor.run("/extra command")
        # The command should not be terminated because the exception happens before
        mock_chat.terminate_command.assert_not_called()

    @patch('ai.chat.chat_command_interceptor.json')
    @patch('builtins.open', new_callable=mock_open)
    @patch('ai.chat.chat_command_interceptor.os.makedirs')
    def test_save_session(self, mock_makedirs, mock_open_func, mock_json, mock_func, interceptor, mock_chat, tmp_path):
        """Tests saving a chat session by verifying json.dump is called correctly."""
        session_filename = "test_session.json"
        mock_chat.messages = [{"role": "user", "content": "Hello"}]
        
        interceptor.save_session(session_filename)
        
        # Verify directory creation
        mock_makedirs.assert_called_once_with(str(tmp_path), exist_ok=True)
        
        # Verify file opening
        expected_path = os.path.join(str(tmp_path), session_filename)
        mock_open_func.assert_called_once_with(expected_path, 'w')
        
        # Get the file handle that 'open' would have returned from the context manager
        file_handle = mock_open_func()
        
        # Verify that json.dump was called with the messages and the file handle
        mock_json.dump.assert_called_once_with(mock_chat.messages, file_handle)
        
        mock_func.out.assert_called_once_with("=== Session saved ===", level="INFO")

    @patch('ai.chat.chat_command_interceptor.os.path.exists')
    def test_load_session_not_found(self, mock_exists, mock_func, interceptor, mock_chat, tmp_path):
        """Tests loading a session that does not exist."""
        session_filename = "nonexistent.json"
        expected_path = os.path.join(str(tmp_path), session_filename)
        mock_exists.return_value = False
        
        interceptor.load_session(session_filename)
        
        mock_exists.assert_called_once_with(expected_path)
        
        mock_func.out.assert_called_once_with("=== Session not found ===", level="WARNING")
        assert mock_chat.messages == [] 

    @patch('ai.chat.chat_command_interceptor.ConsoleChatReader')
    @patch('ai.chat.chat_command_interceptor.os.path.exists')
    def test_load_session_success(self, mock_exists, mock_reader_cls, mock_func, interceptor, mock_chat, tmp_path):
        """Tests successfully loading a session from a file."""
        session_filename = "existent_session.json"
        session_content = [{"role": "user", "content": "Hi there"}]
        expected_path = os.path.join(str(tmp_path), session_filename)
        
        mock_exists.return_value = True
        mock_file_content = json.dumps(session_content)
        
        with patch('builtins.open', mock_open(read_data=mock_file_content)) as mock_file:
            interceptor.load_session(session_filename)
            
            mock_exists.assert_called_once_with(expected_path)
            mock_file.assert_called_once_with(expected_path, 'r')
            
            assert mock_chat.messages == session_content
            
            mock_reader_instance = mock_reader_cls.return_value
            mock_reader_cls.assert_called_once_with(session_filename)
            mock_reader_instance._print_chat.assert_called_once_with(session_content[0])
            
            mock_func.out.assert_called_once_with("=== Session loaded ===", level="WARNING")

    @patch('ai.chat.chat_command_interceptor.os.path.isfile')
    @patch('ai.chat.chat_command_interceptor.os.listdir')
    def test_list_sessions(self, mock_listdir, mock_isfile, mock_func, interceptor, tmp_path):
        """Tests listing saved session files."""
        files_in_dir = ["session1.json", "session2.json", "not_a_file"]
        mock_listdir.return_value = files_in_dir
        
        def isfile_side_effect(path):
            filename = os.path.basename(path)
            return filename in ["session1.json", "session2.json"]
        mock_isfile.side_effect = isfile_side_effect
        
        interceptor.list_sessions()
        
        mock_listdir.assert_called_once_with(str(tmp_path))
        
        expected_calls = [
            call("Chat sessions : "),
            call(ANY),
            call(ANY)
        ]
        mock_func.out.assert_has_calls(expected_calls, any_order=False)
        
        assert mock_func.out.call_count == 3