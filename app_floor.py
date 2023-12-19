import tkinter as tk
from floor import solve, parse_match, forms
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import numpy as np
from gurobipy import GRB
import threading

# list of default constraints, for default display
constraints = [
    ('area', 'box 0 has area of at least 1'),
    ('area', 'box 1 has area of at least 2'),
    ('area', 'box 2 has area of at least 3'),
    ('area', 'box 3 has area of at least 4'),
    ('area', 'box 4 has area of at least 5'),
    ('ratio', 'box 0 has aspect ratio of at least 0.2'),
    ('ratio', 'box 1 has aspect ratio of at least 0.2'),
    ('ratio', 'box 2 has aspect ratio of at least 0.2'),
    ('ratio', 'box 3 has aspect ratio of at least 0.2'),
    ('ratio', 'box 4 has aspect ratio of at least 0.2'),
    ('ratio', 'box 0 has aspect ratio of at most 5'),
    ('ratio', 'box 1 has aspect ratio of at most 5'),
    ('ratio', 'box 2 has aspect ratio of at most 5'),
    ('ratio', 'box 3 has aspect ratio of at most 5'),
    ('ratio', 'box 4 has aspect ratio of at most 5'),
]

# list for storing result from solve()
result = []

def add_constraint():
    """
    Add a constraint to the list and display on the listbox.
    If the constraint is invalid, display an error popup.
    """
    try:
        constraint_type, constraint = type_var.get(), constraint_entry.get()
        parse_match(constraint_type, constraint)
        constraints.append((constraint_type, constraint))
        constraint_list.insert(tk.END, constraint)
    except Exception as e:
        create_error_popup(str(e))

def remove_constraint():
    """Remove the selected constraint from the list and the listbox"""
    selected_index = constraint_list.curselection()
    if selected_index:
        print(selected_index[0])
        constraints.pop(selected_index[0])
        constraint_list.delete(selected_index[0])
        if len(constraints) > 0:
            constraint_list.select_set(min(selected_index[0], len(constraints)-1))

def clear_constraints():
    """Clear all constraints from the list and the listbox"""
    constraints.clear()
    constraint_list.delete(0, tk.END)

def display_text(tktext, text):
    """Display the text in the a Tk.text widget"""
    tktext.config(state=tk.NORMAL)
    tktext.delete(1.0, tk.END)
    tktext.insert(tk.END, text)
    tktext.config(state=tk.DISABLED)

def display_result_text():
    """Display result in the text area"""
    value, W, H, x_arr, y_arr, w_arr, h_arr, model_status = result[0]

    lines = [
        "Result:",
        "- Model status: " + ("Optimal" if model_status == GRB.OPTIMAL else "Inoptimal"),
        f"- Perimeter: {value}",
        f"- Width: {W}",
        f"- Height: {H}"
    ]
    lines.extend([
        f"- Box {i} at ({np.round(x,2)}, {np.round(y,2)}) with w={np.round(w,2)}, h={np.round(h,2)}"
            for i, (x, y, w, h) in enumerate(zip(x_arr, y_arr, w_arr, h_arr))
    ])
    lines.extend([
        "********************",
        f"Applied changes with N={len(x_arr)}",
        "Constraints:"
    ])
    lines.extend([f"- {c}" for _,c in constraints])

    display_text(text_area,'\n'.join(lines))

def display_image():
    """Display the result in the image area, using matplotlib"""
    value, W, H, x_arr, y_arr, w_arr, h_arr, model_status = result[0]

    fig, ax = plt.subplots()
    ax.add_patch(plt.Rectangle((0, 0), W, H, edgecolor='black', facecolor='white'))
    for i, (x, y, w, h) in enumerate(zip(x_arr, y_arr, w_arr, h_arr)):
        ax.add_patch(plt.Rectangle((x, y), w, h, edgecolor='black', facecolor='lightgrey'))
        plt.text(x + w/2, y + h/2, f'{i}', ha='center', va='center')

    plt.xlim(0, W)
    plt.ylim(0, H)
    plt.gca().set_aspect('equal', adjustable='box')
    
    canvas.figure = fig
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    plt.close(fig)

def apply_changes():
    """
    Use the constraints to call solve() and display the result.
    """
    canvas.get_tk_widget().pack_forget()
    display_text(text_area, "Solving...")
    apply_btn.config(state=tk.DISABLED)

    def solve_and_display():
        try:
            N = int(n_entry.get())
            p = float(p_entry.get())
            time_limit = int(float(time_limit_entry.get()))
            result.append(solve(N, p, constraints, time_limit))
        except Exception as e:
            result.append(None)
            create_error_popup(str(e))
            display_text(text_area, "An error has occurred.")


    # Run solve_and_display in a separate thread
    thread = threading.Thread(target=solve_and_display)
    thread.start()
    check_result()

def check_result():
    """
    Check if the result is ready for every 100ms.
    """
    if len(result) == 0:
        root.after(100, check_result)
    elif result[0] is None:
        apply_btn.config(state=tk.NORMAL)
        result.pop()
    else:
        display_result_text()
        display_image()
        apply_btn.config(state=tk.NORMAL)
        result.pop()

def create_entry(form_frame, label_text, row, column, default_value=None):
    """Create a label and an entry in the form frame."""
    # label
    label = tk.Label(form_frame, text=label_text)
    label.grid(row=row, column=column, padx=5)

    # entry
    entry = tk.Entry(form_frame, width=100)
    entry.grid(row=row, column=column+1, padx=5)

    if default_value:
        entry.insert(0, default_value)

    return label, entry

def create_error_popup(error_message):
    """Create a popup window to display an error message."""
    popup = tk.Toplevel()
    popup.title("Error")
    popup.resizable(False, False)
    popup_label = tk.Label(popup, text=error_message)
    popup_label.pack()
    popup_button = tk.Button(popup, text="OK", command=popup.destroy)
    popup_button.pack()

def create_main_window():
    """Create the main window."""
    global root
    root = tk.Tk()
    root.title("Floor Planning Demo")

    # Frames
    frame1 = tk.Frame(root)
    frame1.pack(side=tk.LEFT)

    frame2 = tk.Frame(root)
    frame2.pack(side=tk.LEFT)

    # Image area
    img_label = tk.Label(frame1, text="Image not available", height=25, width=100, bg="white")
    img_label.pack()

    global canvas
    canvas = FigureCanvasTkAgg(master=img_label)

    # Text area
    global text_area
    text_area = tk.Text(frame1, height=25, width=90, state=tk.DISABLED)
    text_area.pack()

    # N, p
    global n_entry, p_entry
    _, n_entry = create_entry(frame2, "Enter N:", 0, 0, "5")
    _, p_entry = create_entry(frame2, "Enter p:", 1, 0, "0")

    # label for type of constraint
    type_label = tk.Label(frame2, text="Constraint type:")
    type_label.grid(row=2, column=0, padx=5)

    # type
    global type_var
    options = list(forms.keys())
    type_var = tk.StringVar(frame2)
    type_var.set(options[0])
    type_option = tk.OptionMenu(frame2, type_var, *options)
    type_option.config(width=100, indicatoron=0, compound='center')
    type_option.grid(row=2, column=1, padx=5)

    # form
    form_label = tk.Label(frame2, text="Input form:")
    form_label.grid(row=3, column=0, padx=5)
    form_text = tk.Text(frame2, height=2, width=100, padx=5, state=tk.DISABLED, font=('Segoe UI', 9))
    form_text.grid(row=3, column=1, padx=5)
    display_text(form_text, forms[type_var.get()])
    type_var.trace_add('write', lambda *args: display_text(form_text, forms[type_var.get()]))

    # constraint
    global constraint_entry
    _, constraint_entry = create_entry(frame2, "Constraint:", 4, 0, forms[type_var.get()])
    type_var.trace_add('write', lambda *args: constraint_entry.delete(0, tk.END) or constraint_entry.insert(0, forms[type_var.get()]))

    # Add button
    add_btn = tk.Button(frame2, text="Add", command=add_constraint)
    add_btn.grid(row=4, column=2, padx=5)

    # constraint list
    global constraint_list
    constraint_list = tk.Listbox(frame2, height=25, width=100)
    constraint_list.grid(row=5, column=1, padx=5)
    # scrollbar
    scrollbar = tk.Scrollbar(frame2)
    scrollbar.grid(row=5, column=2, sticky=tk.N+tk.S+tk.W)
    constraint_list.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=constraint_list.yview)


    for _,c in constraints:
        constraint_list.insert(tk.END, c)

    # time limit
    global time_limit_entry
    _, time_limit_entry = create_entry(frame2, "Time limit (s):", 6, 0, "60")

    # Remove button
    remove_btn = tk.Button(frame2, text="Remove", command=remove_constraint)
    remove_btn.grid(row=7, column=0, padx=5)

    # Apply button
    global apply_btn
    apply_btn = tk.Button(frame2, text="Apply", command=apply_changes)
    apply_btn.grid(row=7, column=1, padx=5)

    # Clear all button
    clear_btn = tk.Button(frame2, text="Clear All", command=clear_constraints)
    clear_btn.grid(row=7, column=2, padx=5)

    # Run
    root.mainloop()

if __name__ == "__main__":
    create_main_window()