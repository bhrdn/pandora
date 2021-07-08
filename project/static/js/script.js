let socket = io();

socket.on('connect', () => {
	let backend_status = document.getElementsByClassName('backend-status')[0];
	backend_status.innerText = 'Backend Started';
	backend_status.classList.add('bg-success');
	backend_status.classList.remove('bg-danger');
});

const menuToggle = (target, hide = false) => {
	for (let t of target) {
		document.getElementById(t).classList.toggle('is-visible');
	}

	if (hide) {
		document.getElementById(hide).classList.remove('is-visible');
	}
};

const followArea = (element) => {
	element.scrollTop = element.scrollHeight;
};

const growArea = (element) => {
	if (element.value.length) {
		element.style.height = `${element.scrollHeight}px`;
	} else {
		element.style.height = '5%';
	}
};

const fuzzerOutput = (message) => {
	let fuzzer_output = document.getElementById('fuzzer-output');
	if (message == 'clear') {
		fuzzer_output.innerText = '';
		document.getElementsByClassName('nav-generation')[0].innerHTML = '';
		document.getElementsByClassName('tab-generation')[0].innerHTML = '';
	} else {
		let time = new Date().toLocaleTimeString().split(' ')[0];
		fuzzer_output.append(`[${time}] ${message}\n`);
	}

	followArea(fuzzer_output);
};

const buttonToggle = () => {
	document.getElementsByClassName('btn-start')[0].disabled =
		!document.getElementsByClassName('btn-start')[0].disabled;
};

// initial datas
new ClipboardJS('.btn');

let currentGeneration,
	currentState = [-1, '???'];
new ClipboardJS('.btn');

let totalStart = 0;

document.getElementById('advance_kre').append('error in your SQL syntax');
document.getElementById('advance_krq').append('-MariaDB');

document.addEventListener(
	'click',
	function (event) {
		if (event.target.classList.contains('btn-config')) {
			menuToggle(['configuration']);
		} else if (event.target.classList.contains('btn-start')) {
			if (totalStart < 1) {
				menuToggle(['logging', 'result'], 'configuration');
			}

			fuzzerOutput('clear');
			buttonToggle();

			let url = document.getElementsByClassName('url')[0].value;
			let cookies = document.getElementsByClassName('cookies')[0].value;

			let general = {
				max_population: Number(
					document.getElementById('general_max_population').value
				),
				max_fetch_chromosome: Number(
					document.getElementById('general_max_chromosome').value
				),
				max_generation: Number(
					document.getElementById('general_max_generation').value
				),
				max_score: Number(document.getElementById('general_max_score').value),
			};

			let advance = {
				timeout_sleep: Number(
					document.getElementById('advance_timeout_sleep').value
				),
				kre: document.getElementById('advance_kre').value.split('\n'),
				krq: document.getElementById('advance_krq').value.split('\n'),
			};

			let approx = {};
			for (let key of ['alpha', 'beta', 'gamma', 'delta']) {
				approx[key] = document.getElementById(`approx_${key}`).value;
			}

			if (!url) {
				fuzzerOutput(
					'Missing url values, please check your input url again !!'
				);
				return buttonToggle();
			}

			approx = Object.keys(approx).map((key) => Number(approx[key]));
			if (approx.reduce((prev, next) => prev + next) > 1) {
				fuzzerOutput('Maximum total approximately is 1');
				return buttonToggle();
			}

			socket.emit('process', {
				target: {
					url,
					cookies,
				},
				config: {
					general,
					approx,
					advance,
				},
			});

			socket.on('logger', (messages) => {
				fuzzerOutput(messages);

				if (messages.includes('Generation:')) {
					let temp = Number(messages.match(/\d+/g).shift());
					if (currentGeneration != temp) {
						currentGeneration = temp;
						currentState = `pandora-${Math.random().toString(36).substring(7)}`;

						document.getElementsByClassName(
							'nav-generation'
						)[0].innerHTML += `<li class="nav-item">
						<button
							class="nav-link ${currentGeneration == 1 ? 'active' : ''}"
							id="${currentState}-tab"
							data-bs-toggle="tab"
							data-bs-target="#${currentState}"
							type="button"
							role="tab"
							aria-controls="${currentState}"
							aria-selected="${currentGeneration == 1 ? 'true' : 'false'}"
						>
							Generation ${currentGeneration}
						</button>
					</li>`;

						document.getElementsByClassName(
							'tab-generation'
						)[0].innerHTML += `<div
						class="tab-pane fade ${currentGeneration == 1 ? 'show active' : ''}"
						id="${currentState}"
						role="tabpanel"
						aria-labelledby="${currentState}-tab"
					>
						<button type="button" class="btn btn-primary btn-sm mt-4 pull-right">
							<i class="bi-download"></i> Download
						</button>

						<table class="table table-sm table-striped table-ellipsis mt-4">
							<thead>
								<tr>
									<th scope="col" class="text-center">#</th>
									<th scope="col" class="text-center">fu_1</th>
									<th scope="col" class="text-center">fu_2</th>
									<th scope="col" class="text-center">fu_3</th>
									<th scope="col" class="text-center">fu_4</th>
									<th scope="col" class="text-center">score_alpha</th>
									<th scope="col" class="text-center">score_beta</th>
									<th scope="col" class="text-center">score_gamma</th>
									<th scope="col" class="text-center">score_delta</th>
									<th scope="col" class="text-center">score_total</th>
									<th scope="col" class="text-center">status</th>
									<th scope="col" class="text-center">action</th>
								</tr>
							</thead>
							<tbody id="table-${currentState}"></tbody>
						</table>
					</div>`;
					}
				}
			});

			socket.on('result', (messages) => {
				for (let i = 0; i < messages.length; i++) {
					let raw_tables = `<tr><th scope="row">${i + 1}</th>`;
					let test_case_result = [];
					let test_case_index = [0, 1, 2, 3];

					for (data of messages[i]) {
						if (i in test_case_index) {
							test_case_result.push(data);
						}

						raw_tables += `<td class="text-center">${data}</td>`;
					}

					raw_tables += '<td class="text-center">';
					if (Number(data) > general.max_score) {
						raw_tables += '<span class="badge bg-danger">Vulnerable</span>';
					} else if (Number(data) > general.max_score * (40 / 100)) {
						raw_tables +=
							'<span class="badge bg-warning">False Positive</span>';
					} else {
						raw_tables += '<span class="badge bg-secondary">N/A</span>';
					}
					raw_tables += '</td>';

					raw_tables += `
					<td class="text-center">
						<button type="button" class="btn btn-secondary btn-sm" data-clipboard-text="${encodeURI(
							test_case_result.join(' ')
						)}">
							<i class="bi-clipboard"></i>
						</button>
					</td></tr>`;

					document.getElementById(`table-${currentState}`).innerHTML +=
						raw_tables;
				}
			});
			socket.on('finished', () => buttonToggle());

			totalStart -= -1;
		} else if (event.target.classList.contains('logging-clear')) {
			fuzzerOutput('clear');
		} else return;

		event.preventDefault();
	},
	false
);
