from tail_tagger.file_operations import FileOperations

TAGS = ["digital_media_(artwork)", "solo"]


def test_output_with_spaces():
    assert FileOperations.format_tags_for_output(TAGS, False) == "digital media (artwork), solo"


def test_output_with_underscores():
    assert FileOperations.format_tags_for_output(TAGS, True) == "digital_media_(artwork), solo"
