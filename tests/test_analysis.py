from fbi_wanted_analysis.analysis import add, run_analysis_pipeline


def test_run_analysis_pipeline_prints_message(capsys):
	run_analysis_pipeline()
	captured = capsys.readouterr()
	assert "Running analysis pipeline..." in captured.out


def test_add_handles_various_numbers():
	assert add(1, 2) == 3
	assert add(-1, 5) == 4
	assert add(-3, -4) == -7
