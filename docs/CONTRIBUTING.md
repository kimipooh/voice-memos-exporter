# Contributing to Voice Memos Exporter

We love your input! We want to make contributing to Voice Memos Exporter as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process
We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Local Development
1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate virtual environment: 
   - Windows: `venv\Scripts\activate`
   - Unix/MacOS: `source venv/bin/activate`
4. Run both front ends: `python3 export_voice_memos.py --help` and `python3 voice_memos_exporter.py`
5. Run the tests: `python3 -m unittest discover -s tests -v`

## License
This project is licensed under the MIT License; see [LICENSE](../LICENSE).
The upstream project `rudrakabir/voice-memos-exporter` publishes the same MIT
License. By contributing, you agree that your contributions are licensed under
the MIT License.
