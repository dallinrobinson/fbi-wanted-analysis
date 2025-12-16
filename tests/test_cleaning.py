from fbi_wanted_analysis.cleaning import run_cleaning_pipeling


def test_run_cleaning_pipeline_prints_message(capsys):
	run_cleaning_pipeling()
	captured = capsys.readouterr()
	assert "Running cleaning pipeline..." in captured.out
