from coauthor_interface.backend.access_code import AccessCodeConfig


class TestAccessCodeConfig:
    """Test cases for AccessCodeConfig class."""

    def test_init_with_empty_row(self):
        """Test initialization with empty row dictionary."""
        config = AccessCodeConfig({})

        # Check default values
        assert config.domain == "demo"
        assert config.example == "na"
        assert config.prompt == "na"
        assert config.engine == "text-davinci-003"
        assert config.session_length == 0
        assert config.n == 5
        assert config.max_tokens == 50
        assert config.temperature == 0.95
        assert config.top_p == 1
        assert config.presence_penalty == 0.5
        assert config.frequency_penalty == 0.5
        assert config.stop == ["."]
        assert config.additional_data is None
        assert config.show_interventions is False

    def test_init_with_partial_row(self):
        """Test initialization with partial row data."""
        row = {
            "domain": "test_domain",
            "example": "test_example",
            "prompt": "test_prompt",
        }
        config = AccessCodeConfig(row)

        # Check updated values
        assert config.domain == "test_domain"
        assert config.example == "test_example"
        assert config.prompt == "test_prompt"

        # Check that other values remain default
        assert config.engine == "text-davinci-003"
        assert config.session_length == 0
        assert config.n == 5

    def test_init_with_numeric_values(self):
        """Test initialization with numeric values."""
        row = {
            "session_length": "10",
            "n": "3",
            "max_tokens": "100",
            "temperature": "0.8",
            "top_p": "0.9",
            "presence_penalty": "0.3",
            "frequency_penalty": "0.7",
        }
        config = AccessCodeConfig(row)

        assert config.session_length == 10
        assert config.n == 3
        assert config.max_tokens == 100
        assert config.temperature == 0.8
        assert config.top_p == 0.9
        assert config.presence_penalty == 0.3
        assert config.frequency_penalty == 0.7

    def test_init_with_stop_tokens(self):
        """Test initialization with stop tokens."""
        row = {"stop": "end|stop|finish"}
        config = AccessCodeConfig(row)

        assert config.stop == ["end", "stop", "finish"]

    def test_init_with_stop_tokens_with_newlines(self):
        """Test initialization with stop tokens containing newline escapes."""
        row = {"stop": "end\\n|stop\\n|finish"}
        config = AccessCodeConfig(row)

        assert config.stop == ["end\n", "stop\n", "finish"]

    def test_init_with_additional_data(self):
        """Test initialization with additional data."""
        row = {"additional_data": "some_extra_data"}
        config = AccessCodeConfig(row)

        assert config.additional_data == "some_extra_data"

    def test_init_with_additional_data_na(self):
        """Test initialization with additional_data set to 'na'."""
        row = {"additional_data": "na"}
        config = AccessCodeConfig(row)

        assert config.additional_data is None

    def test_init_with_engine(self):
        """Test initialization with custom engine."""
        row = {"engine": "gpt-4"}
        config = AccessCodeConfig(row)

        assert config.engine == "gpt-4"

    def test_init_with_show_interventions_true(self):
        """Test initialization with show_interventions set to 'true'."""
        row = {"show_interventions": "true"}
        config = AccessCodeConfig(row)

        assert config.show_interventions is True

    def test_init_with_show_interventions_false(self):
        """Test initialization with show_interventions set to 'false'."""
        row = {"show_interventions": "false"}
        config = AccessCodeConfig(row)

        assert config.show_interventions is False

    def test_init_with_show_interventions_mixed_case(self):
        """Test initialization with show_interventions in mixed case."""
        row = {"show_interventions": "TRUE"}
        config = AccessCodeConfig(row)

        assert config.show_interventions is True

    def test_convert_to_dict(self):
        """Test convert_to_dict method returns correct dictionary."""
        config = AccessCodeConfig({})
        result = config.convert_to_dict()

        expected = {
            "domain": "demo",
            "example": "na",
            "prompt": "na",
            "session_length": 0,
            "n": 5,
            "max_tokens": 50,
            "temperature": 0.95,
            "top_p": 1,
            "presence_penalty": 0.5,
            "frequency_penalty": 0.5,
            "stop": ["."],
            "engine": "text-davinci-003",
            "additional_data": None,
            "show_interventions": False,
        }

        assert result == expected

    def test_convert_to_dict_with_custom_values(self):
        """Test convert_to_dict method with custom values."""
        row = {
            "domain": "custom_domain",
            "example": "custom_example",
            "prompt": "custom_prompt",
            "session_length": "15",
            "n": "7",
            "max_tokens": "200",
            "temperature": "0.7",
            "top_p": "0.8",
            "presence_penalty": "0.2",
            "frequency_penalty": "0.3",
            "stop": "end|stop",
            "engine": "gpt-4",
            "additional_data": "custom_data",
            "show_interventions": "true",
        }
        config = AccessCodeConfig(row)
        result = config.convert_to_dict()

        expected = {
            "domain": "custom_domain",
            "example": "custom_example",
            "prompt": "custom_prompt",
            "session_length": 15,
            "n": 7,
            "max_tokens": 200,
            "temperature": 0.7,
            "top_p": 0.8,
            "presence_penalty": 0.2,
            "frequency_penalty": 0.3,
            "stop": ["end", "stop"],
            "engine": "gpt-4",
            "additional_data": "custom_data",
            "show_interventions": True,
        }

        assert result == expected

    def test_update_method(self):
        """Test update method modifies existing configuration."""
        config = AccessCodeConfig({})

        # Verify initial state
        assert config.domain == "demo"
        assert config.n == 5

        # Update with new values
        update_row = {"domain": "updated_domain", "n": "10"}
        config.update(update_row)

        # Verify updated values
        assert config.domain == "updated_domain"
        assert config.n == 10

        # Verify unchanged values
        assert config.example == "na"
        assert config.max_tokens == 50

    def test_update_method_with_all_fields(self):
        """Test update method with all possible fields."""
        config = AccessCodeConfig({})

        update_row = {
            "domain": "full_domain",
            "example": "full_example",
            "prompt": "full_prompt",
            "session_length": "20",
            "n": "8",
            "max_tokens": "150",
            "temperature": "0.6",
            "top_p": "0.7",
            "presence_penalty": "0.1",
            "frequency_penalty": "0.2",
            "stop": "full|complete|done",
            "engine": "gpt-3.5-turbo",
            "additional_data": "full_data",
            "show_interventions": "true",
        }

        config.update(update_row)

        assert config.domain == "full_domain"
        assert config.example == "full_example"
        assert config.prompt == "full_prompt"
        assert config.session_length == 20
        assert config.n == 8
        assert config.max_tokens == 150
        assert config.temperature == 0.6
        assert config.top_p == 0.7
        assert config.presence_penalty == 0.1
        assert config.frequency_penalty == 0.2
        assert config.stop == ["full", "complete", "done"]
        assert config.engine == "gpt-3.5-turbo"
        assert config.additional_data == "full_data"
        assert config.show_interventions is True

    def test_edge_case_empty_stop_string(self):
        """Test edge case with empty stop string."""
        row = {"stop": ""}
        config = AccessCodeConfig(row)

        assert config.stop == [""]

    def test_edge_case_single_stop_token(self):
        """Test edge case with single stop token."""
        row = {"stop": "end"}
        config = AccessCodeConfig(row)

        assert config.stop == ["end"]

    def test_edge_case_stop_tokens_with_pipe_only(self):
        """Test edge case with stop tokens containing only pipe."""
        row = {"stop": "|"}
        config = AccessCodeConfig(row)

        assert config.stop == ["", ""]

    def test_edge_case_show_interventions_invalid_value(self):
        """Test edge case with invalid show_interventions value."""
        row = {"show_interventions": "invalid"}
        config = AccessCodeConfig(row)

        assert config.show_interventions is False

    def test_edge_case_show_interventions_empty_string(self):
        """Test edge case with empty show_interventions string."""
        row = {"show_interventions": ""}
        config = AccessCodeConfig(row)

        assert config.show_interventions is False

    def test_edge_case_numeric_strings_with_spaces(self):
        """Test edge case with numeric strings containing spaces."""
        row = {
            "session_length": " 10 ",
            "n": " 5 ",
            "max_tokens": " 100 ",
            "temperature": " 0.8 ",
            "top_p": " 0.9 ",
            "presence_penalty": " 0.3 ",
            "frequency_penalty": " 0.7 ",
        }
        config = AccessCodeConfig(row)

        assert config.session_length == 10
        assert config.n == 5
        assert config.max_tokens == 100
        assert config.temperature == 0.8
        assert config.top_p == 0.9
        assert config.presence_penalty == 0.3
        assert config.frequency_penalty == 0.7

    def test_comprehensive_integration(self):
        """Test comprehensive integration of all features."""
        # Create config with initial values
        initial_row = {"domain": "initial_domain", "n": "3", "temperature": "0.5"}
        config = AccessCodeConfig(initial_row)

        # Verify initial state
        assert config.domain == "initial_domain"
        assert config.n == 3
        assert config.temperature == 0.5
        assert config.engine == "text-davinci-003"  # default

        # Update with new values
        update_row = {
            "domain": "updated_domain",
            "engine": "gpt-4",
            "show_interventions": "true",
            "stop": "end|stop\\n|finish",
        }
        config.update(update_row)

        # Verify final state
        assert config.domain == "updated_domain"
        assert config.n == 3  # unchanged
        assert config.temperature == 0.5  # unchanged
        assert config.engine == "gpt-4"
        assert config.show_interventions is True
        assert config.stop == ["end", "stop\n", "finish"]

        # Test convert_to_dict
        result_dict = config.convert_to_dict()
        assert result_dict["domain"] == "updated_domain"
        assert result_dict["n"] == 3
        assert result_dict["temperature"] == 0.5
        assert result_dict["engine"] == "gpt-4"
        assert result_dict["show_interventions"] is True
        assert result_dict["stop"] == ["end", "stop\n", "finish"]
