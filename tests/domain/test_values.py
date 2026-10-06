import pytest

from eleicoes.domain.errors import (
    EmptyElectionScopeError,
    InvalidElectionYearError,
    InvalidPackageRefError,
    InvalidRemoteZipError,
    InvalidTurnoError,
    InvalidUfError,
)
from eleicoes.domain.values import (
    MAX_ELECTION_YEAR,
    MIN_ELECTION_YEAR,
    UF_CODES,
    UF_NAMES,
    DiscoveryRequest,
    ElectionYear,
    PackageRef,
    RemoteZip,
    Turno,
    Uf,
    default_turnos,
    default_ufs,
    uf_name,
)


class TestElectionYear:
    def test_accepts_bounds(self) -> None:
        assert ElectionYear(MIN_ELECTION_YEAR).value == MIN_ELECTION_YEAR
        assert ElectionYear(MAX_ELECTION_YEAR).value == MAX_ELECTION_YEAR

    def test_accepts_a_real_election_year(self) -> None:
        assert ElectionYear(2022).value == 2022

    @pytest.mark.parametrize("value", [1993, 2101, 0, -1, True])
    def test_rejects_year_outside_guard(self, value: int) -> None:
        with pytest.raises(InvalidElectionYearError):
            ElectionYear(value)


class TestTurno:
    @pytest.mark.parametrize("value", [1, 2])
    def test_accepts_first_and_second_turn(self, value: int) -> None:
        assert Turno(value).value == value

    @pytest.mark.parametrize("value", [0, 3, -1, True])
    def test_rejects_unknown_turn(self, value: int) -> None:
        with pytest.raises(InvalidTurnoError):
            Turno(value)


class TestUf:
    def test_accepts_every_official_code_including_abroad(self) -> None:
        assert len(UF_CODES) == 28
        assert "ZZ" in UF_CODES
        for code in UF_CODES:
            assert Uf(code).code == code

    def test_normalizes_lowercase(self) -> None:
        assert Uf("sp").code == "SP"

    def test_every_uf_code_has_a_name(self) -> None:
        expected = {
            "AC": "Acre",
            "AL": "Alagoas",
            "AM": "Amazonas",
            "AP": "Amapá",
            "BA": "Bahia",
            "CE": "Ceará",
            "DF": "Distrito Federal",
            "ES": "Espírito Santo",
            "GO": "Goiás",
            "MA": "Maranhão",
            "MT": "Mato Grosso",
            "MS": "Mato Grosso do Sul",
            "MG": "Minas Gerais",
            "PA": "Pará",
            "PB": "Paraíba",
            "PE": "Pernambuco",
            "PI": "Piauí",
            "PR": "Paraná",
            "RJ": "Rio de Janeiro",
            "RN": "Rio Grande do Norte",
            "RS": "Rio Grande do Sul",
            "RO": "Rondônia",
            "RR": "Roraima",
            "SC": "Santa Catarina",
            "SP": "São Paulo",
            "SE": "Sergipe",
            "TO": "Tocantins",
            "ZZ": "Exterior",
        }
        assert set(UF_NAMES) == set(UF_CODES)
        assert expected == UF_NAMES
        for code in UF_CODES:
            assert uf_name(code) == expected[code]
            assert uf_name(code.lower()) == expected[code]

    @pytest.mark.parametrize("value", ["", "BR", "XX", "S", "SPP"])
    def test_rejects_unknown_code(self, value: str) -> None:
        with pytest.raises(InvalidUfError):
            Uf(value)


class TestRemoteZip:
    def test_accepts_https_zip(self) -> None:
        archive = RemoteZip(
            url="https://cdn.tse.jus.br/estatistica/file.zip",
            filename="file.zip",
        )
        assert archive.filename == "file.zip"

    @pytest.mark.parametrize(
        "filename",
        ["file.zip.sha512", "file.csv", "", "../file.zip", "a/b.zip", "file.ZIP.sha512"],
    )
    def test_rejects_non_payload_names(self, filename: str) -> None:
        with pytest.raises(InvalidRemoteZipError):
            RemoteZip(url="https://cdn.tse.jus.br/file", filename=filename)

    def test_rejects_non_http_url(self) -> None:
        with pytest.raises(InvalidRemoteZipError):
            RemoteZip(url="ftp://cdn.tse.jus.br/file.zip", filename="file.zip")


class TestScopeAndPackageRef:
    def test_rejects_empty_turnos_and_ufs(self) -> None:
        year = ElectionYear(2022)
        with pytest.raises(EmptyElectionScopeError):
            DiscoveryRequest(year=year, turnos=(), ufs=default_ufs())
        with pytest.raises(EmptyElectionScopeError):
            DiscoveryRequest(year=year, turnos=default_turnos(), ufs=())

    def test_blank_overrides_become_absent(self) -> None:
        request = DiscoveryRequest(
            year=ElectionYear(2022),
            turnos=default_turnos(),
            ufs=default_ufs(),
            cdn_directory="  ",
            dataset_ref="",
        )
        assert request.cdn_directory is None
        assert request.dataset_ref is None

    @pytest.mark.parametrize(
        ("raw", "package_id"),
        [
            ("meu-pacote", "meu-pacote"),
            (
                "https://dadosabertos.tse.jus.br/dataset/resultados-2022-arquivos/",
                "resultados-2022-arquivos",
            ),
            (
                "https://dadosabertos.tse.jus.br/api/3/action/package_show?id=outro-pacote",
                "outro-pacote",
            ),
        ],
    )
    def test_parses_package_id_from_ref(self, raw: str, package_id: str) -> None:
        assert PackageRef.parse(raw).package_id == package_id

    @pytest.mark.parametrize("raw", ["", "   ", "https://example.com/", "a/b"])
    def test_rejects_blank_package_ref(self, raw: str) -> None:
        with pytest.raises(InvalidPackageRefError):
            PackageRef.parse(raw)
