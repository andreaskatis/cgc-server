class coverageUpdater {
	constructor() {
		this.views = []
	}

	addView(view) {
		this.views.push(view)
	}

	removeView(view) {
		var newviews = this.views.filter(function(item){
			return view == item;
		});
		this.views = newviews;
	}

	_updateCoverageResponse(coverage) {
		for (view in this.views) {
			view.update(coverage)
		}
	}

	_updateCoverage() {
		$.getJSON("/session/" + sid + "/coverage/" + currentFile, this._updateCoverageResponse)
			.fail(function(jqxhr, textStatus, error) {
				console.log("Request Failed: " + textStatus + ", " + error);
			})
			.always(function(jqxhr, textStatus, error) {
				console.log("Request Failed: " + textStatus + ", " + error);
			});
	}
}

class coverageView extends EventTarget {
	constructor(domParent) {
		super();
		this.listeners = [];
		this.domParent = domParent
	}

	update() {}
	draw() {}
}

class coverageTreeView extends coverageView {

	constructor(id) {
		super(id);
		this.tree = new Object();
		this.sources = new Object();
		this.files = [];
		this.root = {};
		this.root.container = document.createElement("div");
		this.root.children = {};
		this.root.container.className = "list-group"
		this.root.name = "";
		$(id).append(this.root.container).addClass("coverage-tree-view");


		this.link = document.createElement("a");
		this.link.innerHTML = `
		<div class="progress coverage-progress">
		<div class="progress-bar coverage-progress-bar" role="progressbar" style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
		</div>`

		this.container = document.createElement("div");
		this.container.className = "list-group collapse";
	}

	path() {
		var path = this.name;
		var node = this.parent_node;
		while (node.name) {
			path = node.name + "/" + path;
			node = node.parent_node;
		}
		return path;
	}

	_draw(files) {
		for (var f in files) {
				var parts = files[f].file.split('/');
				var node = this.root;
				var p;
				for (p = 0; p < parts.length - 1; p++) {
					var key = "_" + parts[p] + "_";
					node = node.children[key] || (this._createDir(node, parts[p]));
				}
				key = "_" + parts[p] + "_";
				node = node.children[key] || (this._createFile(node, parts[p]));
				node.lines_executed = files[f].lines_executed;
				node.lines_total = files[f].lines_total;
		}
	}

	update(coverage) {
		this._draw(coverage.files);
		for(var c in this.root.children) {
			this.root.children[c].update_totals();
		}	
	}

	leafClickedEvent() {
		var ev = new CustomEvent("leafClicked", {detail: this.coverageTreeNode});
		this.coverageTree.dispatchEvent(ev);
	}

	_createDir(parent_node, dir) {
		var node = new Object();
		node.update_totals = function () {
			var new_lines_executed = 0;
			this.lines_total = 0;
			for(var c in this.children) {
				var child = this.children[c];
				child.update_totals();
				new_lines_executed += child.lines_executed;
				this.lines_total += child.lines_total;
			}
			if (this.lines_executed != new_lines_executed) {
				this.lines_executed = new_lines_executed;
				$(".coverage-progress-bar", this.dom)
				.width(((this.lines_executed / this.lines_total) * 100) + "%")
				.text(this.lines_executed + "/" + this.lines_total);
			}
		};
		node.children = {};
		var link = this.link.cloneNode(true);
		var glyph = document.createElement("i")
		var dir_id = '_' + Math.random().toString(36).substr(2, 9)
		glyph.className = "fas fa-angle-right"
		link.setAttribute('data-toggle', 'collapse');
		link.setAttribute('href', "#" + dir_id);
		link.insertBefore(document.createTextNode(dir), link.childNodes[0]);
		link.insertBefore(glyph, link.childNodes[0]);
		link.addEventListener('click', function() {
			$('.fas', this)
				.toggleClass('fa-angle-right')
				.toggleClass('fa-angle-down')
		});

		var child_container = document.createElement("div");
		child_container.setAttribute("id", dir_id)
		child_container.className = "list-group collapse"
		parent_node.container.appendChild(link)
		parent_node.container.appendChild(child_container);
		parent_node.children["_" + dir + "_"] = node;
		node.dom = link;
		node.container = child_container;
		node.name = dir;
		node.parent_node = parent_node;
		node.path = this.path;
		return node;
	}

	_createFile(parent_node, file) {
		var node = new Object();
		var link = this.link.cloneNode(true);
		node.update_totals = function () {
			$(".coverage-progress-bar", this.dom)
			.width(((this.lines_executed / this.lines_total) * 100) + "%")
			.text(this.lines_executed + "/" + this.lines_total);
		};
		link.href = "#"
		link.insertBefore(document.createTextNode(file), link.childNodes[0]);
		link.addEventListener('click', this.leafClickedEvent)
		link.coverageTree = this;
		link.coverageTreeNode = node;
		parent_node.container.appendChild(link)
		parent_node.children["_" + file + "_"] = node;
		node.dom = link;
		node.name = file;
		node.parent_node = parent_node;
		node.path = this.path;
		return node;
	}
}

class coverageSourceView extends coverageView {
	constructor(domParent, prefix="") {
		super(domParent)
		this.id = '_' + Math.random().toString(36).substr(2, 9)
		this.prefix = prefix
		this._draw()
		this.coverage = []
	}

	setPrefix(prefix) {
		this.prefix = prefix;
	}

	setSourceFile(file) {
		var that = this;
		var lnum = 0;
		this.file = file;
		$.ajax({
			type: "GET",
			url: that.prefix + "/" + that.file,
			success: function(content) {
				var lines = content.split('\n');
				$('#' + that.id + ' table tbody')
				.html(lines.map(function(l) {
					lnum += 1;
					return "<tr class=\"coverage-source-line\"><td class=\"linenum\">" + lnum + "</td><td class=\"count\"></td><td>" + l + "</td></tr>";
				}));
				that._update_counts();
			},
			error: function() {
				console.log('error');
			}
		});
	}

	_draw() {
		var div = document.createElement("div");
		div.innerHTML =
		`<table><thead>
			<tr><th class=\"col-lnum\">line</th><th class=\"col-count\">count</th><th class=\"col-source\">source</th></tr>
		</thead><tbody></tbody></table>`;
		div.className = "coverage-source-view";
		div.setAttribute("id", this.id)
		this.domParent.append(div);
	}

	_update_counts() {
		for (var f in this.coverage.files) {
			if (this.coverage.files[f].file == this.file) {
				var fileCounts = this.coverage.files[f];
				break;
			}
		}
		if (typeof(fileCounts) === "undefined")
			return;
		var domlines = $('#' + this.id + ' table tbody tr')
		var lines = fileCounts.lines;
		if (typeof(lines) !== "undefined") {
			var l;
			for (l in lines) {
				var dl = lines[l].line_number - 1;
				if (!domlines[dl])
					break;
				if (domlines[dl].children[1].dataset.count != lines[l].count) {
					domlines[dl].children[1].dataset.count = lines[l].count;
					domlines[dl].children[1].textContent = lines[l].count;
					domlines[dl].dataset.count = lines[l].count;
				}
			}
		}
	}

	update(coverage) {
		this.coverage = coverage;
		this._update_counts();
	}
}
