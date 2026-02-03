from tools.tafsir_gui.utils.gcp_instructions import generate_instructions


def test_generate_instructions_deterministic():
    instr = generate_instructions("My Project", billing_country="US", org_folder="org1")
    assert "My Project" not in instr.console_block  # slugged
    assert "projectselector2" in instr.console_block
    assert "generative-language" in instr.console_block.lower()
    assert instr.urls["credentials"].startswith("https://console.cloud.google.com/apis/credentials")
    assert len(instr.steps) >= 5
    assert "gcloud services enable" in instr.cli_block
