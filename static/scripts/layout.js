document.getElementById('menuIcon').addEventListener('click', () => {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('main');
    const mainHeader = document.querySelector('.main-header');
    sidebar.classList.toggle('closed');
    mainContent.classList.toggle('shifted');

    if (sidebar.classList.contains('closed')) {
        mainHeader.style.left = '80px';
    } else {
        mainHeader.style.left = '250px';
    }
});

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('loginuser').value = '';
    document.getElementById('loginpwd').value = '';

});


document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded and parsed');
    const addOnPrices = {
        "Honey": 20.00,
        "Syrup": 10.00,
        "Crystal Jelly": 15.00,
        "Chia Seeds": 10.00,
        "None": 0.00,
    };

    function updatePrice(selectElement) {
        const productCard = selectElement.closest('.product-card');
        if (!productCard) {
            console.error('Product card not found');
            return;
        }

        const productId = productCard.dataset.productId;

        if (selectElement.classList.contains('size-dropdown')) {
            const size = selectElement.value;
            fetch('/get_price', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        product_id: productId,
                        size: size
                    })
                })
                .then(response => response.json())
                .then(data => {
                    const priceElement = document.getElementById(`price-${productId}`);
                    if (priceElement) {
                        if (data.price) {
                            priceElement.innerText = `₱${parseFloat(data.price).toFixed(2)}`;
                            priceElement.dataset.basePrice = parseFloat(data.price);
                            priceElement.dataset.price = parseFloat(data.price);
                            recalculateTotal();
                        }
                    }
                })
                .catch(error => console.error('Error:', error));
        } else if (selectElement.classList.contains('addson-dropdown')) {
            const selectedAddOn = selectElement.value;
            const addOnPrice = addOnPrices[selectedAddOn] || 0;

            console.log(`Selected Add-On: ${selectedAddOn}, Price: ${addOnPrice}`);
            const priceElement = document.getElementById(`price-${productId}`);
            if (priceElement) {
                const basePrice = parseFloat(priceElement.dataset.basePrice || 0);
                const newPrice = basePrice + addOnPrice;

                priceElement.innerText = `₱${newPrice.toFixed(2)}`;
                priceElement.dataset.price = newPrice;
                recalculateTotal();
            }
        }
    }

    function recalculateTotal() {
        let itemTotal = 0;
        document.querySelectorAll('.order-container').forEach(orderContainer => {
            const priceElement = orderContainer.querySelector('.price-value');
            const quantity = parseInt(orderContainer.querySelector('.item-quantity span').innerText.split(':')[1].trim(), 10);

            if (priceElement && priceElement.dataset.price) {
                const price = parseFloat(priceElement.dataset.price);
                itemTotal += price * quantity;
            }
        });

        const deliveryFee = 10.00;
        const orderTotal = itemTotal + deliveryFee;

        document.querySelector('.order-summary span:nth-child(2)').innerText = `₱${itemTotal.toFixed(2)}`;
        document.querySelector('#order-total strong').innerText = `₱${orderTotal.toFixed(2)}`;
    }

    const placeOrderButton = document.querySelector('.order-btn');

    function validateSelections() {
        let allSelected = true;

        const cartItems = document.querySelectorAll('.order-container');
        if (cartItems.length === 0) {
            allSelected = false;
        }
        cartItems.forEach(item => {
            const sizeDropdown = item.querySelector('.size-dropdown');
            const addOnDropdown = item.querySelector('.addson-dropdown');

            if (!sizeDropdown || !sizeDropdown.value) {
                allSelected = false;
            }

            if (!addOnDropdown || !addOnDropdown.value) {
                allSelected = false;
            }
        });
        const deliveryAddress = document.querySelector('.delivery-address');
        if (!deliveryAddress || !deliveryAddress.value.trim()) {
            allSelected = false;
        }

        placeOrderButton.disabled = !allSelected;
    }

    document.querySelectorAll('.size-dropdown, .addson-dropdown').forEach(dropdown => {
        dropdown.addEventListener('change', (event) => {
            updatePrice(event.target);
            validateSelections();
        });
    });

    const deliveryAddressField = document.querySelector('.delivery-address');
    if (deliveryAddressField) {
        deliveryAddressField.addEventListener('input', validateSelections);
    }

    validateSelections();

    var today = new Date().toISOString().split('T')[0];
    var oneMonthFromToday = new Date();
    oneMonthFromToday.setMonth(oneMonthFromToday.getMonth() + 1);
    var maxDate = oneMonthFromToday.toISOString().split('T')[0];

    document.getElementById('delivery-date').setAttribute('min', today);
    document.getElementById('delivery-date').setAttribute('max', maxDate);
    document.getElementById('delivery-date').value = today;
});


document.addEventListener('DOMContentLoaded', () => {
    const placeOrderButton = document.querySelector('.order-btn');
    const cartContainers = document.querySelectorAll('.order-container');

    placeOrderButton.disabled = true;

    function updateButtonState() {
        const allSelectionsValid = validateSelections();
        console.log("Valid selections:", allSelectionsValid);
        placeOrderButton.disabled = !allSelectionsValid;
    }

    placeOrderButton.addEventListener('click', async (event) => {
        event.preventDefault();

        const cartItems = [];
        const deliveryAddress = document.querySelector('.delivery-address').value.trim();
        const deliveryDate = document.querySelector('#delivery-date').value.trim();
        const orderNotes = document.querySelector('#notes').value.trim();

        cartContainers.forEach((container) => {
            const productCard = container.querySelector('.product-card');
            const productId = productCard.dataset.productId;

            const sizeDropdown = productCard.querySelector('.size-dropdown');
            const size = sizeDropdown ? sizeDropdown.value : '';

            const quantityInput = productCard.querySelector('.quantity-input');
            const quantity = quantityInput ? parseInt(quantityInput.value, 10) : 1;

            const addOnDropdown = container.querySelector(`#addson-dropdown-${productId}`);
            const addOn = addOnDropdown ? addOnDropdown.value : null;

            let addOnPrice = 0;
            if (addOn) {
                const addOnElement = addOnDropdown.querySelector(`option[value="${addOn}"]`);
                if (addOnElement && addOnElement.dataset.price) {
                    addOnPrice = parseFloat(addOnElement.dataset.price);
                }
            }

            if (productId && size) {
                cartItems.push({
                    product_id: productId,
                    size: size,
                    quantity: quantity,
                    add_on: addOn,
                    add_on_price: addOnPrice,
                });
            }
        });

        console.log('Cart Items:', cartItems);

        const allSelectionsValid = validateSelections();
        if (!allSelectionsValid) {
            alert('Please ensure all required fields are selected.');
            return;
        }

        if (!deliveryAddress || !deliveryDate) {
            alert('Please fill in all required fields.');
            return;
        }

        if (cartItems.length === 0) {
            alert('Your cart is empty.');
            return;
        }

        const payload = {
            order_items: cartItems,
            delivery_address: deliveryAddress,
            delivery_date: deliveryDate,
            order_notes: orderNotes,
        };

        console.log('Payload:', payload);

        try {
            const response = await fetch('/place_order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });

            if (response.ok) {
                const data = await response.json();
                console.log('Order Response:', data);
                if (data.success) {
                    alert('Order placed successfully!');
                    window.location.href = '/products';
                } else {
                    alert(`Error: ${data.message}`);
                }
            } else {
                const error = await response.json();
                alert(`Error: ${error.message || 'Failed to place order'}`);
            }
        } catch (error) {
            console.error('Error placing order:', error);
            alert('An error occurred. Please try again.');
        }
    });

    function validateSelections() {
        let allValid = true;

        cartContainers.forEach((item) => {
            const sizeDropdown = item.querySelector('.size-dropdown');
            const addOnDropdown = item.querySelector('.addson-dropdown');

            if (!sizeDropdown || !sizeDropdown.value) {
                console.log('Size selection is missing or empty');
                allValid = false;
            }
            if (!addOnDropdown || !addOnDropdown.value) {
                console.log('Add-on selection is missing or empty');
                allValid = false;
            }
        });

        const deliveryAddress = document.querySelector('.delivery-address').value.trim();
        const deliveryDate = document.querySelector('#delivery-date').value.trim();

        if (!deliveryAddress || !deliveryDate) {
            console.log('Delivery address or date is missing');
            allValid = false;
        }

        return allValid;
    }
    cartContainers.forEach((container) => {
        const sizeDropdown = container.querySelector('.size-dropdown');
        const addOnDropdown = container.querySelector('.addson-dropdown');

        if (sizeDropdown) {
            sizeDropdown.addEventListener('change', updateButtonState);
        }

        if (addOnDropdown) {
            addOnDropdown.addEventListener('change', updateButtonState);
        }
    });

    document.querySelector('.delivery-address').addEventListener('input', updateButtonState);
    document.querySelector('#delivery-date').addEventListener('input', updateButtonState);
});




document.addEventListener("DOMContentLoaded", function() {
    fetchAndDisplayData('/api/products', '#productsTableBody', renderProductRow);
    fetchAndDisplayData('/api/employees', '#employeesTableBody', renderEmployeeRow);
    fetchAndDisplayData('/api/reviews', '#reviewsTableBody', renderReviewRow);

    function fetchAndDisplayData(apiUrl, tableBodySelector, renderRowFunction) {
        fetch(apiUrl)
            .then(response => response.json())
            .then(data => {
                const tableBody = document.querySelector(tableBodySelector);
                tableBody.innerHTML = data.map(renderRowFunction).join('');
            })
            .catch(error => console.error(`Error fetching data from ${apiUrl}:`, error));
    }

    function renderProductRow(product) {
        return `
            <tr>
                <td>${product.productid}</td>
                <td>${product.name}</td>
                <td>${product.category}</td>
                <td>${product.description}</td>
                <td>
                    <button class="btn btn-warning btn-sm" onclick="editProduct(${product.productid})">Edit</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteProduct(${product.productid})">Delete</button>
                </td>
            </tr>`;
    }

    function renderEmployeeRow(employee) {
        return `
            <tr>
                <td>${employee.id}</td>
                <td>${employee.Name}</td>
                <td>${employee.Email}</td>
                <td>${employee.Privilege}</td>
                <td>
                    <button class="btn btn-warning btn-sm" onclick="editEmployee(${employee.id})">Edit</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteEmployee(${employee.id})">Delete</button>
                </td>
            </tr>`;
    }

    function renderReviewRow(review) {
        return `
            <tr>
                <td>${review.reviewid}</td>
                <td>${review.customerid}</td>
                <td>${review.feedback}</td>
                <td>
                    <button class="btn btn-danger btn-sm" onclick="deleteReview(${review.reviewid})">Delete</button>
                </td>
            </tr>`;
    }

    function addEditEntity(apiUrl, formData, method = 'POST') {
        fetch(apiUrl, {
                method: method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData),
            })
            .then(response => response.json())
            .then(() => location.reload())
            .catch(error => console.error(`Error ${method === 'POST' ? 'adding' : 'editing'} entity:`, error));
    }

    function deleteEntity(apiUrl, idField, idValue) {
        fetch(apiUrl, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    [idField]: idValue
                }),
            })
            .then(response => response.json())
            .then(() => location.reload())
            .catch(error => console.error(`Error deleting entity:`, error));
    }

    window.editProduct = function(productId) {};

    window.deleteProduct = function(productId) {
        if (confirm('Are you sure you want to delete this product?')) {
            deleteEntity('/api/products', 'productid', productId);
        }
    };

    window.editEmployee = function(employeeId) {};

    window.deleteEmployee = function(employeeId) {
        if (confirm('Are you sure you want to delete this employee?')) {
            deleteEntity('/api/employees', 'id', employeeId);
        }
    };

    window.deleteReview = function(reviewId) {
        if (confirm('Are you sure you want to delete this review?')) {
            deleteEntity('/api/reviews', 'reviewid', reviewId);
        }
    };
});


function addEmployee() {
    const employeeData = {
        firstname: document.getElementById('employeeFirstName').value,
        lastname: document.getElementById('employeeLastName').value,
        username: document.getElementById('employeeUsername').value,
        email: document.getElementById('employeeEmail').value,
        hashedpassword: document.getElementById('employeePassword').value,
        privilege: document.getElementById('employeePrivilege').value,
    };

    fetch('/api/employees', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(employeeData),
        })
        .then((response) => response.json())
        .then((data) => {
            if (data.success) {
                alert('Employee added successfully!');
                location.reload();
            } else {
                alert(`Failed to add employee: ${data.error}`);
            }
        })
        .catch((error) => console.error('Error:', error));
}


function editEmployee(employeeid) {
    const employeeData = {
        employeeid: employeeid,
        firstname: document.getElementById(`firstname-${employeeid}`).value,
        lastname: document.getElementById(`lastname-${employeeid}`).value,
        username: document.getElementById(`username-${employeeid}`).value,
        email: document.getElementById(`email-${employeeid}`).value,
        address: document.getElementById(`address-${employeeid}`).value,
        phone_number: document.getElementById(`phone_number-${employeeid}`).value,
    };

    fetch('/api/employees', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(employeeData),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Employee updated successfully!');
                location.reload();
            } else {
                alert(`Failed to update employee: ${data.error}`);
            }
        })
        .catch(error => console.error('Error:', error));
}

function deleteEmployee(employeeid) {
    fetch('/api/employees', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                employeeid
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Employee deleted successfully!');
                location.reload();
            } else {
                alert(`Failed to delete employee: ${data.error}`);
            }
        })
        .catch(error => console.error('Error:', error));
}




async function fetchAndDisplayData(apiUrl, tableBodySelector, rowRenderer) {
    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`Failed to fetch data from ${apiUrl}: ${response.statusText}`);
        }

        const data = await response.json();
        const tableBody = document.querySelector(tableBodySelector);
        tableBody.innerHTML = "";

        data.forEach(order => {
            const row = rowRenderer(order);
            tableBody.appendChild(row);
        });
    } catch (error) {
        console.error("Error fetching and displaying data:", error);
    }
}

async function markOrderAsCompleted(orderId) {
    try {
        const response = await fetch(`/api/orders/${orderId}/complete`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (response.ok) {
            alert(`Order ${orderId} marked as completed.`);

            fetchAndDisplayData('/api/orders', '#ordersTableBody', renderOrderRow);
        } else {
            const error = await response.json();
            alert(`Failed to update order: ${error.message}`);
        }
    } catch (error) {
        console.error("Error updating order:", error);
        alert("An error occurred while updating the order.");
    }
}

function renderOrderRow(order) {
    const row = document.createElement("tr");

    const productDetails = order.products
        .map(product => `${product.name} (${product.quantity})${product.variant_name ? ` - ${product.variant_name}` : ''}`)
        .join(", ");

    const cells = [
        order.orderid,
        productDetails,
        order.products.reduce((sum, product) => sum + product.quantity, 0),
        order.products.map(product => product.variant_name || "N/A").join(", "),
        order.products.map(product => product.addons || "None").join(", "),
        order.products.reduce((sum, product) => sum + product.subtotal, 0).toFixed(2),
        order.orderdate,
        order.totalamount.toFixed(2),
        order.delivery_address,
        order.order_notes || "No Notes",
        order.status
    ];

    cells.forEach(text => {
        const cell = document.createElement("td");
        cell.textContent = text;
        row.appendChild(cell);
    });


    const actionCell = document.createElement("td");
    if (order.status !== "Completed") {
        const completeButton = document.createElement("button");
        completeButton.textContent = "Mark as Completed";
        completeButton.classList.add("btn", "btn-success", "btn-sm");
        completeButton.addEventListener("click", () => markOrderAsCompleted(order.orderid));
        actionCell.appendChild(completeButton);
    } else {
        actionCell.textContent = "completed";
    }
    row.appendChild(actionCell);

    return row;
}



document.addEventListener('DOMContentLoaded', () => {
    fetchAndDisplayData('/api/orders', '#ordersTableBody', renderOrderRow);
});
