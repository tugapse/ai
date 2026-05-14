import pytest
from unittest.mock import MagicMock, patch, call, ANY

from ai.chat.chat import Chat, ChatRoles, PrefixCompleter
from core.llms.base_llm import BaseModel
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.completion import Completion, CompleteEvent
from prompt_toolkit.document import Document

# It's good practice to patch where the object is looked up.
# Chat uses 'func.out', so we patch 'ai.chat.chat.func'.
# It also uses prompt_toolkit, let's patch that at the class level.
@pytest.fixture
def mock_chat_dependencies():
    """Mocks dependencies for the Chat class that are not the main focus of unit tests."""
    with patch('ai.chat.chat.PromptSession') as mock_session, \
         patch('ai.chat.chat.KeyBindings') as mock_kb, \
         patch('ai.chat.chat.func') as mock_func, \
         patch('ai.chat.chat.os') as mock_os:
        
        # Configure mock_os for file operations
        mock_os.path.isfile.return_value = False
        mock_os.path.isdir.return_value = False
        mock_os.sep = '/'

        yield {
            "session": mock_session,
            "kb": mock_kb,
            "func": mock_func,
            "os": mock_os
        }

@pytest.fixture
def chat_instance(mock_chat_dependencies):
    """Fixture to create a Chat instance with mocked dependencies for each test."""
    chat = Chat(commands=["/test", "/agent"], agents=["test_agent"])
    # Mock the trigger method from the parent Events class to intercept events
    chat.trigger = MagicMock()
    return chat

class TestChatInitialization:
    def test_init_default_values(self, chat_instance: Chat):
        """Tests that the Chat class initializes with correct default values."""
        assert not chat_instance.terminate
        assert not chat_instance.running_command
        assert not chat_instance.waiting_for_response
        assert chat_instance.messages == []
        assert not chat_instance.agent_mode_active
        assert not chat_instance.multiline_mode
        assert chat_instance.commands == ["/test", "/agent"]
        assert chat_instance.agents == ["test_agent"]
        assert chat_instance.pending_files == {}
        assert isinstance(chat_instance.completer, PrefixCompleter)

class TestChatStateManagement:
    def test_update_suggestions(self, chat_instance: Chat):
        """Tests if command and agent lists are updated dynamically."""
        chat_instance.update_suggestions(commands=["/new_cmd"], agents=["new_agent"])
        assert chat_instance.commands == ["/new_cmd"]
        assert chat_instance.agents == ["new_agent"]
        
        # Test partial update (only commands)
        chat_instance.update_suggestions(commands=["/another_cmd"])
        assert chat_instance.commands == ["/another_cmd"]
        assert chat_instance.agents == ["new_agent"] # Should remain unchanged

    def test_terminate_chat(self, chat_instance: Chat, mock_chat_dependencies):
        """Tests the termination of the chat session."""
        chat_instance.terminate_chat()
        assert chat_instance.terminate is True
        mock_chat_dependencies["func"].out.assert_called_with(ANY)

    def test_terminate_command(self, chat_instance: Chat):
        """Tests setting the running_command flag to False."""
        chat_instance.running_command = True
        chat_instance.terminate_command()
        assert not chat_instance.running_command

    def test_chat_finished(self, chat_instance: Chat):
        """Tests the state transition after an assistant's response is complete."""
        chat_instance.waiting_for_response = True
        chat_instance.current_message = "  response message  "
        chat_instance.chat_finished()
        
        assert not chat_instance.waiting_for_response
        assert chat_instance.current_message == ""
        assert len(chat_instance.messages) == 1
        
        last_message = chat_instance.messages[0]
        assert last_message["role"] == ChatRoles.ASSISTANT
        assert last_message["content"] == "response message"

class TestMessageHandling:
    def test_add_message(self, chat_instance: Chat):
        """Tests adding a message to the history."""
        message = BaseModel.create_message(ChatRoles.USER, "hello")
        chat_instance._add_message(message)
        assert chat_instance.messages == [message]

    def test_add_message_caching_disabled(self, chat_instance: Chat):
        """Tests that messages are not stored when caching is disabled."""
        chat_instance.cache_messages = False
        message = BaseModel.create_message(ChatRoles.USER, "hello")
        chat_instance._add_message(message)
        assert chat_instance.messages == []

    def test_check_messages_size_trims_history(self, chat_instance: Chat):
        """Tests that the message history is trimmed to max_chat_log."""
        chat_instance.max_chat_log = 3
        for i in range(5):
            chat_instance._add_message(BaseModel.create_message(ChatRoles.USER, f"msg {i}"))
        
        assert len(chat_instance.messages) == 3
        assert chat_instance.messages[0]["content"] == "msg 2"
        assert chat_instance.messages[2]["content"] == "msg 4"

    def test_reset_chat(self, chat_instance: Chat):
        """Tests that the chat state is fully reset."""
        chat_instance.messages = [1, 2, 3]
        chat_instance.pending_files = {"a": "b"}
        chat_instance.top_bar_content = ["info"]
        
        chat_instance._reset_chat()
        
        assert chat_instance.messages == []
        assert chat_instance.pending_files == {}
        assert chat_instance.top_bar_content == []

class TestCommandHandling:
    def test_run_command_clear(self, chat_instance: Chat, mock_chat_dependencies):
        """Tests the `/clear` command."""
        chat_instance.messages = [1]
        chat_instance.pending_files = {"a": "b"}
        
        chat_instance.run_command("/clear")
        
        assert chat_instance.messages == []
        assert chat_instance.pending_files == {}
        assert not chat_instance.running_command
        mock_chat_dependencies["func"].out.assert_called_with(ANY)

    def test_run_command_agent_mode(self, chat_instance: Chat, mock_chat_dependencies):
        """Tests the `/agent` command to activate agent mode."""
        chat_instance.run_command("/agent")
        
        assert chat_instance.agent_mode_active is True
        assert not chat_instance.running_command
        mock_chat_dependencies["func"].out.assert_called_with(ANY)

    def test_run_command_triggers_event(self, chat_instance: Chat):
        """Tests that other commands trigger the EVENT_COMMAND_STARTED."""
        command_text = "/some_other_command"
        chat_instance.run_command(command_text)
        
        assert chat_instance.running_command is True
        chat_instance.trigger.assert_called_once_with(chat_instance.EVENT_COMMAND_STARTED, command_text)

class TestChatInteraction:
    def test_send_chat_triggers_event(self, chat_instance: Chat):
        """Tests that send_chat triggers the correct event and updates state."""
        message_content = "Hello, world!"
        chat_instance.send_chat(message_content)

        assert chat_instance.waiting_for_response is True
        assert len(chat_instance.messages) == 1
        assert chat_instance.messages[0]["role"] == ChatRoles.USER
        assert chat_instance.messages[0]["content"] == message_content
        chat_instance.trigger.assert_called_once_with(chat_instance.EVENT_CHAT_SENT, message_content)

    def test_handle_file_attachment_success(self, chat_instance: Chat, mock_chat_dependencies):
        """Tests staging a file for the next message."""
        mock_os = mock_chat_dependencies['os']
        mock_func = mock_chat_dependencies['func']

        file_path = "/fake/path/test.txt"
        file_content = "This is a test file."
        
        mock_os.path.isfile.return_value = True
        mock_os.path.basename.return_value = "test.txt"

        with patch('builtins.open', new=MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=file_content)))))) as mock_open:
            chat_instance._handle_file_attachment(f"@{file_path}")

            mock_os.path.isfile.assert_called_with(file_path)
            mock_open.assert_called_with(file_path, 'r')
            assert chat_instance.pending_files == {file_path: file_content}
            mock_func.out.assert_called_with(ANY) # Check for success message

    def test_handle_file_attachment_not_found(self, chat_instance: Chat, mock_chat_dependencies):
        """Tests handling a file that does not exist."""
        mock_os = mock_chat_dependencies['os']
        mock_func = mock_chat_dependencies['func']
        
        file_path = "/fake/path/not_found.txt"
        mock_os.path.isfile.return_value = False
        
        chat_instance._handle_file_attachment(f"@{file_path}")
        
        assert chat_instance.pending_files == {}
        mock_func.out.assert_called_with(ANY) # Check for error message

    def test_handle_file_attachment_read_error(self, chat_instance: Chat, mock_chat_dependencies):
        """Tests handling an exception during file reading."""
        mock_os = mock_chat_dependencies['os']
        mock_func = mock_chat_dependencies['func']

        file_path = "/fake/path/test.txt"
        mock_os.path.isfile.return_value = True
        
        with patch('builtins.open', new=MagicMock()) as mock_open:
            mock_open.side_effect = Exception("Permission denied")
            chat_instance._handle_file_attachment(f"@{file_path}")

            assert chat_instance.pending_files == {}
            mock_func.out.assert_called_with(ANY) # Check for error message


class TestPrefixCompleter:
    @pytest.fixture
    def completer(self):
        """Fixture for PrefixCompleter."""
        return PrefixCompleter(commands=['/help', '/load', '/save'])

    @staticmethod
    def _create_mock_entry(name, is_dir):
        """Helper to create a mock os.DirEntry."""
        entry = MagicMock()
        entry.name = name
        entry.is_dir.return_value = is_dir
        return entry

    @staticmethod
    def _setup_mock_os(mock_os, scandir_return=[]):
        """Helper to configure a mock os module for file completion tests."""
        mock_os.sep = '/'
        mock_os.path.isdir.return_value = True
        mock_os.path.join.side_effect = lambda *args: '/'.join(arg.strip('/') for arg in args if arg)
        mock_os.scandir.return_value = scandir_return
        return mock_os

    def test_command_completion(self, completer):
        """Tests command completion for prefixed text."""
        doc = Document('/lo', cursor_position=3)
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        
        assert len(completions) == 1
        assert completions[0].text == '/load'

    def test_no_completion_for_non_prefix(self, completer):
        """Tests that no command completions are offered for non-prefixed text."""
        doc = Document('hello', cursor_position=5)
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))
        
        assert len(completions) == 0

    @patch('ai.chat.chat.os')
    def test_file_completion_in_directory(self, mock_os, completer):
        """Tests file and directory path completion."""
        scandir_return = [
            self._create_mock_entry('a_dir', is_dir=True),
            self._create_mock_entry('a_file.txt', is_dir=False)
        ]
        self._setup_mock_os(mock_os, scandir_return=scandir_return)

        doc = Document('@some/path/', cursor_position=11)
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))

        mock_os.path.isdir.assert_called_with('some/path/')
        mock_os.scandir.assert_called_with('some/path/')
        
        assert len(completions) == 2
        assert completions[0].text == 'some/path/a_dir/'
        assert completions[1].text == 'some/path/a_file.txt'

    @patch('ai.chat.chat.os')
    def test_file_completion_partial_name(self, mock_os, completer):
        """Tests file completion with a partial filename."""
        scandir_return = [self._create_mock_entry('application.log', is_dir=False)]
        self._setup_mock_os(mock_os, scandir_return=scandir_return)

        doc = Document('@app', cursor_position=4)
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))

        mock_os.scandir.assert_called_with('.')
        assert len(completions) == 1
        assert completions[0].text == 'application.log'

    @patch('ai.chat.chat.os')
    def test_file_completion_ignores_dotfiles(self, mock_os, completer):
        """Tests that dotfiles are ignored when the query does not start with a dot."""
        scandir_return = [
            self._create_mock_entry('.env', is_dir=False),
            self._create_mock_entry('main.py', is_dir=False)
        ]
        self._setup_mock_os(mock_os, scandir_return=scandir_return)

        doc = Document('@m', cursor_position=2)
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))

        assert len(completions) == 1
        assert completions[0].text == 'main.py'

    @patch('ai.chat.chat.os')
    def test_file_completion_includes_dotfiles(self, mock_os, completer):
        """Tests that dotfiles are included when the query starts with a dot."""
        scandir_return = [
            self._create_mock_entry('.env', is_dir=False),
            self._create_mock_entry('main.py', is_dir=False)
        ]
        self._setup_mock_os(mock_os, scandir_return=scandir_return)

        doc = Document('@.', cursor_position=2)
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))

        # It should match .env but not main.py
        assert len(completions) == 1
        assert completions[0].text == '.env'

    @patch('ai.chat.chat.os')
    def test_file_completion_no_match_on_at_only(self, mock_os, completer):
        """Tests that no completions are returned for just the '@' symbol."""
        scandir_return = [self._create_mock_entry('main.py', is_dir=False)]
        self._setup_mock_os(mock_os, scandir_return=scandir_return)

        doc = Document('@', cursor_position=1)
        event = CompleteEvent()
        completions = list(completer.get_completions(doc, event))

        assert len(completions) == 0

    @patch('ai.chat.chat.os')
    def test_file_completion_permission_error(self, mock_os, completer):
        """Tests that a PermissionError is handled gracefully."""
        self._setup_mock_os(mock_os)
        mock_os.scandir.side_effect = PermissionError
        
        doc = Document('@some/locked/dir/', cursor_position=17)
        event = CompleteEvent()
        
        completions = list(completer.get_completions(doc, event))
        
        assert len(completions) == 0