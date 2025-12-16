from fbi_wanted_analysis.analysis import run_analysis_pipeline


def test_run_analysis_pipeline_prints_message(capsys):
    run_analysis_pipeline()
    captured = capsys.readouterr()
    assert "Running analysis pipeline..." in captured.out
