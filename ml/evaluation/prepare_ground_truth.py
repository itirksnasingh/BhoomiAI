from pathlib import Path
import csv
import html


ROOT = Path(__file__).resolve().parents[2]

EVALUATION_DIR = ROOT / "data" / "evaluation"
RENDERED_DIR = EVALUATION_DIR / "rendered"

HTML_FILE = EVALUATION_DIR / "field_ground_truth_annotation.html"
CSV_FILE = EVALUATION_DIR / "field_ground_truth.csv"


FIELDS = [
    ("document_type", "Document Type"),
    ("village", "Village"),
    ("taluka", "Taluka"),
    ("survey_gat_number", "Survey / Gat Number"),
    ("sub_division", "Sub-division"),
    ("account_number", "Account Number"),
    ("holder_name", "Occupant / Holder Name"),
    ("cultivable_area", "Cultivable Area"),
    ("land_tenure", "Land Tenure / System"),
    ("local_field_name", "Local Field Name"),
]


STATUS_OPTIONS = [
    ("", "Select status"),
    ("present", "Present"),
    ("not_visible", "Not visible / Not applicable"),
    ("unreadable", "Present but unreadable"),
]


def esc(value):
    return html.escape(str(value), quote=True)


def build_field_html(index, field_name, label):
    options = []

    for value, text in STATUS_OPTIONS:
        selected = " selected" if value == "" else ""

        options.append(
            f'<option value="{esc(value)}"{selected}>{esc(text)}</option>'
        )

    return f"""
    <div class="field-row">

        <div class="field-label">
            {esc(label)}
        </div>

        <div class="field-controls">

            <select
                id="status-{field_name}-{index}"
                data-status-for="{field_name}"
            >
                {''.join(options)}
            </select>

            <input
                id="value-{field_name}-{index}"
                data-value-for="{field_name}"
                type="text"
                placeholder="Enter value only when status is Present"
                disabled
            >

        </div>

    </div>
    """


def main():

    images = sorted(RENDERED_DIR.glob("*.png"))

    if not images:
        print()
        print("ERROR: No rendered PNG files found.")
        print(f"Expected folder: {RENDERED_DIR}")
        print()
        return

    field_names = []

    for field_name, label in FIELDS:
        field_names.append(field_name)
        field_names.append(f"{field_name}_status")


    # ---------------------------------------------------------
    # Create CSV template
    # ---------------------------------------------------------

    with CSV_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            ["image"] + field_names
        )

        for image_path in images:

            writer.writerow(
                [f"data/evaluation/rendered/{image_path.name}"]
                + ["" for _ in field_names]
            )


    # ---------------------------------------------------------
    # Create HTML cards
    # ---------------------------------------------------------

    cards = []

    for index, image_path in enumerate(images):

        fields_html = []

        for field_name, label in FIELDS:

            fields_html.append(
                build_field_html(
                    index,
                    field_name,
                    label
                )
            )


        cards.append(
            f"""
            <section
                class="sample"
                data-index="{index}"
                data-image="{esc(image_path.name)}"
            >

                <div class="sample-header">

                    <h2>
                        Sample {index + 1} / {len(images)}
                        — {esc(image_path.name)}
                    </h2>

                    <span
                        class="sample-status"
                        id="sample-status-{index}"
                    >
                        0 / {len(FIELDS)} reviewed
                    </span>

                </div>


                <div class="grid">

                    <div class="panel">

                        <div class="panel-title">
                            Scanned Document
                        </div>

                        <div class="image-container">

                            <img
                                src="rendered/{esc(image_path.name)}"
                                alt="{esc(image_path.name)}"
                            >

                        </div>

                    </div>


                    <div class="panel">

                        <div class="panel-title">
                            Ground Truth Fields
                        </div>

                        <div class="fields">

                            {''.join(fields_html)}

                        </div>

                    </div>

                </div>

            </section>
            """
        )


    cards_html = "\n".join(cards)


    # ---------------------------------------------------------
    # Full HTML
    # ---------------------------------------------------------

    html_content = f"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
BhoomiAI — Field Ground Truth
</title>


<style>

* {{
    box-sizing: border-box;
}}


body {{
    margin: 0;

    background: #f3f4f6;

    color: #111827;

    font-family:
        Arial,
        Helvetica,
        sans-serif;
}}


header {{
    position: sticky;

    top: 0;

    z-index: 50;

    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 20px;

    padding: 14px 20px;

    background: white;

    border-bottom:
        1px solid #d1d5db;
}}


header h1 {{
    margin: 0;

    font-size: 20px;
}}


.header-actions {{
    display: flex;

    align-items: center;

    gap: 10px;
}}


button {{
    border: 0;

    border-radius: 7px;

    padding:
        10px 15px;

    background: #166534;

    color: white;

    font-size: 14px;

    cursor: pointer;
}}


button.secondary {{
    background: #4b5563;
}}


button:hover {{
    opacity: 0.92;
}}


.container {{
    max-width: 1500px;

    margin: 0 auto;

    padding: 20px;
}}


.instructions {{
    margin-bottom: 20px;

    padding: 16px;

    background: white;

    border:
        1px solid #d1d5db;

    border-radius: 10px;

    line-height: 1.55;
}}


#overall-progress {{
    margin-top: 12px;

    font-weight: bold;
}}


.sample {{
    margin-bottom: 30px;

    padding: 16px;

    background: white;

    border:
        1px solid #d1d5db;

    border-radius: 10px;
}}


.sample-header {{
    display: flex;

    align-items: center;

    justify-content: space-between;

    gap: 10px;

    margin-bottom: 14px;
}}


.sample-header h2 {{
    margin: 0;

    font-size: 17px;
}}


.sample-status {{
    font-size: 13px;

    font-weight: bold;

    white-space: nowrap;
}}


.grid {{
    display: grid;

    grid-template-columns:
        1.15fr
        1fr;

    gap: 16px;
}}


.panel {{
    overflow: hidden;

    background: #fafafa;

    border:
        1px solid #d1d5db;

    border-radius: 8px;
}}


.panel-title {{
    padding:
        10px 12px;

    background: #eef2f7;

    border-bottom:
        1px solid #d1d5db;

    font-weight: bold;
}}


.image-container {{
    max-height: 850px;

    overflow: auto;

    padding: 10px;

    background: #e5e7eb;
}}


.image-container img {{
    display: block;

    width: 100%;

    height: auto;

    background: white;
}}


.fields {{
    padding: 14px;
}}


.field-row {{
    margin-bottom: 14px;

    padding-bottom: 14px;

    border-bottom:
        1px solid #e5e7eb;
}}


.field-row:last-child {{
    border-bottom: none;

    margin-bottom: 0;

    padding-bottom: 0;
}}


.field-label {{
    margin-bottom: 6px;

    font-size: 14px;

    font-weight: bold;
}}


.field-controls {{
    display: grid;

    grid-template-columns:
        190px
        1fr;

    gap: 8px;
}}


.field-controls select,
.field-controls input {{
    width: 100%;

    min-width: 0;

    padding:
        9px 10px;

    border:
        1px solid #cbd5e1;

    border-radius: 6px;

    background: white;

    font-size: 14px;

    outline: none;
}}


.field-controls input:disabled {{
    background: #f3f4f6;

    color: #9ca3af;
}}


.field-controls select:focus,
.field-controls input:focus {{
    border-color: #64748b;
}}


.complete {{
    color: #166534;
}}


.incomplete {{
    color: #92400e;
}}


@media (max-width: 1000px) {{

    .grid {{
        grid-template-columns: 1fr;
    }}

    .field-controls {{
        grid-template-columns: 1fr;
    }}

    header {{
        position: static;

        align-items: flex-start;

        flex-direction: column;
    }}

    .header-actions {{
        flex-wrap: wrap;
    }}

}}

</style>

</head>


<body>


<header>

<h1>
BhoomiAI — Field Ground Truth
</h1>


<div class="header-actions">

<button
    class="secondary"
    onclick="clearSavedWork()"
>
Clear Saved Work
</button>


<button
    onclick="downloadCSV()"
>
Download field_ground_truth.csv
</button>

</div>

</header>


<div class="container">


<div class="instructions">

<strong>
How to annotate
</strong>


<p>
For each field, choose one status:
<strong>Present</strong>,
<strong>Not visible / Not applicable</strong>,
or
<strong>Present but unreadable</strong>.
</p>


<p>
Choose <strong>Present</strong> only when the value is actually visible
and readable. Then enter the value exactly as shown in the document.
</p>


<p>
Choose <strong>Not visible / Not applicable</strong> when that field
does not appear on this page.
</p>


<p>
Choose <strong>Present but unreadable</strong> when the field appears
to exist but you cannot reliably determine its value.
</p>


<p>
<strong>Do not guess.</strong>
</p>


<div id="overall-progress">
Loading...
</div>

</div>


{cards_html}


</div>


<script>


const STORAGE_KEY =
    "bhoomiai_field_ground_truth_v3";


const fieldNames = [
"""

    for field_name, label in FIELDS:
        html_content += f"""
    "{field_name}",
"""

    html_content += r"""
];


function updateFieldState(select) {

    const field =
        select.getAttribute("data-status-for");

    const section =
        select.closest(".sample");

    const index =
        section.getAttribute("data-index");

    const input =
        document.getElementById(
            "value-" +
            field +
            "-" +
            index
        );

    if (
        select.value === "present"
    ) {

        input.disabled = false;

    } else {

        input.disabled = true;
        input.value = "";

    }

    saveWork();

    updateProgress();
}


function saveWork() {

    const data = {};

    document
        .querySelectorAll(".sample")
        .forEach(function(section) {

            const index =
                section.getAttribute("data-index");

            const item = {};

            fieldNames.forEach(function(field) {

                const status =
                    document.getElementById(
                        "status-" +
                        field +
                        "-" +
                        index
                    );

                const value =
                    document.getElementById(
                        "value-" +
                        field +
                        "-" +
                        index
                    );

                item[field] =
                    status.value;

                item[field + "_value"] =
                    value.value;

            });

            data[index] = item;

        });


    localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(data)
    );
}


function restoreWork() {

    const raw =
        localStorage.getItem(
            STORAGE_KEY
        );

    if (!raw) {
        return;
    }


    let data;

    try {

        data = JSON.parse(raw);

    } catch (error) {

        return;
    }


    Object.keys(data).forEach(function(index) {

        const item =
            data[index];


        fieldNames.forEach(function(field) {

            const status =
                document.getElementById(
                    "status-" +
                    field +
                    "-" +
                    index
                );

            const value =
                document.getElementById(
                    "value-" +
                    field +
                    "-" +
                    index
                );


            if (!status || !value) {
                return;
            }


            status.value =
                item[field] || "";


            value.value =
                item[field + "_value"] || "";


            if (
                status.value === "present"
            ) {

                value.disabled = false;

            } else {

                value.disabled = true;

            }

        });

    });
}


function updateProgress() {

    const sections =
        document.querySelectorAll(".sample");

    let totalReviewed = 0;

    let totalFields =
        sections.length *
        fieldNames.length;


    sections.forEach(function(section) {

        const index =
            section.getAttribute("data-index");

        let reviewed = 0;


        fieldNames.forEach(function(field) {

            const status =
                document.getElementById(
                    "status-" +
                    field +
                    "-" +
                    index
                );


            if (
                status &&
                status.value !== ""
            ) {

                reviewed++;

                totalReviewed++;

            }

        });


        const statusLabel =
            document.getElementById(
                "sample-status-" +
                index
            );


        statusLabel.textContent =
            reviewed +
            " / " +
            fieldNames.length +
            " reviewed";


        if (
            reviewed === fieldNames.length
        ) {

            statusLabel.className =
                "sample-status complete";

        } else {

            statusLabel.className =
                "sample-status incomplete";

        }

    });


    document.getElementById(
        "overall-progress"
    ).textContent =
        "Overall progress: " +
        totalReviewed +
        " / " +
        totalFields +
        " fields reviewed";
}


function clearSavedWork() {

    const confirmed =
        confirm(
            "Clear all saved annotation work?"
        );


    if (!confirmed) {
        return;
    }


    localStorage.removeItem(
        STORAGE_KEY
    );


    location.reload();
}


function csvEscape(value) {

    return '"' +
        String(value || "")
            .replace(/"/g, '""')
            .replace(/\r\n/g, "\n")
            .replace(/\r/g, "\n") +
        '"';
}


function downloadCSV() {

    const sections =
        document.querySelectorAll(".sample");


    let csv = "image";


    fieldNames.forEach(function(field) {

        csv +=
            "," +
            csvEscape(field);

        csv +=
            "," +
            csvEscape(
                field + "_status"
            );

    });


    csv += "\r\n";


    sections.forEach(function(section) {

        const image =
            section.getAttribute(
                "data-image"
            );


        csv +=
            csvEscape(
                "data/evaluation/rendered/" +
                image
            );


        const index =
            section.getAttribute(
                "data-index"
            );


        fieldNames.forEach(function(field) {

            const status =
                document.getElementById(
                    "status-" +
                    field +
                    "-" +
                    index
                );


            const value =
                document.getElementById(
                    "value-" +
                    field +
                    "-" +
                    index
                );


            csv +=
                "," +
                csvEscape(
                    value
                        ? value.value.trim()
                        : ""
                );


            csv +=
                "," +
                csvEscape(
                    status
                        ? status.value
                        : ""
                );

        });


        csv += "\r\n";

    });


    const blob =
        new Blob(
            ["\uFEFF" + csv],
            {
                type:
                    "text/csv;charset=utf-8"
            }
        );


    const url =
        URL.createObjectURL(blob);


    const link =
        document.createElement("a");


    link.href = url;

    link.download =
        "field_ground_truth.csv";


    document.body.appendChild(link);

    link.click();

    document.body.removeChild(link);


    URL.revokeObjectURL(url);
}


document
    .querySelectorAll(
        "select[data-status-for]"
    )
    .forEach(function(select) {

        select.addEventListener(
            "change",
            function() {
                updateFieldState(select);
            }
        );

    });


document
    .querySelectorAll(
        "input[data-value-for]"
    )
    .forEach(function(input) {

        input.addEventListener(
            "input",
            function() {

                saveWork();
                updateProgress();

            }
        );

    });


restoreWork();

updateProgress();

</script>


</body>

</html>
"""


    HTML_FILE.write_text(
        html_content,
        encoding="utf-8"
    )


    print()
    print("Samples found:", len(images))
    print("Fields per sample:", len(FIELDS))
    print()
    print("HTML:")
    print(HTML_FILE)
    print()
    print("CSV:")
    print(CSV_FILE)
    print()
    print("Annotation tool generated successfully.")
    print()


if __name__ == "__main__":
    main()