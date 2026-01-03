from github_api_app.job_description import JobDescription
from github_api_app.matcher import match_profile_to_jd


def _jd(required, optional):
    return JobDescription(
        name="JD",
        version=1,
        job_id="ORG-TEST-1",
        skills_required=required,
        skills_optional=optional,
        activity={},
        scoring={},
    )


def _profile(evidence):
    return {"username": "u", "evidence": evidence, "activity": {}}


def test_all_required_pass():
    jd = _jd(["python", "ci"], ["documentation", "code_quality", "api_development"])
    profile = _profile({"python": True, "ci": True})
    res = match_profile_to_jd(profile, jd)
    assert res.status == "PASS"


def test_none_required_fail():
    jd = _jd(["python", "ci"], ["documentation", "code_quality"])
    profile = _profile(
        {"python": False, "ci": False, "documentation": True, "code_quality": True}
    )
    res = match_profile_to_jd(profile, jd)
    assert res.status == "FAIL"


def test_half_required_and_two_optional_pass():
    jd = _jd(
        ["python", "ci", "testing", "iac"],
        ["documentation", "code_quality", "api_development"],
    )
    # 2/4 required = 50% and 2 optional matched => PASS
    profile = _profile(
        {
            "python": True,
            "ci": True,
            "testing": False,
            "iac": False,
            "documentation": True,
            "code_quality": True,
        }
    )
    res = match_profile_to_jd(profile, jd)
    assert res.status == "PASS"


def test_half_required_but_only_one_optional_fail():
    jd = _jd(
        ["python", "ci", "testing", "iac"],
        ["documentation", "code_quality", "api_development"],
    )
    # 2/4 required = 50% but only 1 optional => FAIL
    profile = _profile(
        {
            "python": True,
            "ci": True,
            "testing": False,
            "iac": False,
            "documentation": True,
        }
    )
    res = match_profile_to_jd(profile, jd)
    assert res.status == "FAIL"


def test_more_than_half_required_but_zero_optional_fail():
    jd = _jd(["python", "ci", "testing", "iac"], ["documentation", "code_quality"])
    # 3/4 required >=50% but 0 optional => FAIL (per your rules)
    profile = _profile({"python": True, "ci": True, "testing": True, "iac": False})
    res = match_profile_to_jd(profile, jd)
    assert res.status == "FAIL"


def test_less_than_half_required_fail_even_with_optional():
    jd = _jd(
        ["python", "ci", "testing", "iac"],
        ["documentation", "code_quality", "api_development"],
    )
    # 1/4 required < 50% => FAIL even if optional is strong
    profile = _profile(
        {
            "python": True,
            "documentation": True,
            "code_quality": True,
            "api_development": True,
        }
    )
    res = match_profile_to_jd(profile, jd)
    assert res.status == "FAIL"
