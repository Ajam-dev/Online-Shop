"use strict"

document.addEventListener("DOMContentLoaded", function() {
    const variantsElement = document.getElementById("variants-data");

    if (!variantsElement) {
        return;
    }

    const variants = JSON.parse(variantsElement.textContent);

    const selectors = Array.from(document.querySelectorAll(".variant-attribute-select"));

    const information = document.getElementById("variant-information");
    const skuElement = document.getElementById("variant-sku");

    const originalPriceContainer = document.getElementById("variant-original-price-container");
    const originalPriceElement = document.getElementById("variant-original-price");

    const discountContainer = document.getElementById("variant-discount-container");
    const discountElement = document.getElementById("variant-discount");

    const finalPriceElement = document.getElementById("variant-final-price");
    const stockElement = document.getElementById("variant-stock");

    const imageElement = document.getElementById("variant-image");
    const messageElement = document.getElementById("variant-message");

    const selectedVariantInput = document.getElementById("selected-variant-id");
    const addToCartButton = document.getElementById("add-to-cart-button");

    if (
        !selectors.length ||
        !information ||
        !skuElement ||
        !originalPriceContainer ||
        !originalPriceElement ||
        !discountContainer ||
        !discountElement ||
        !finalPriceElement ||
        !stockElement ||
        !imageElement ||
        !messageElement ||
        !selectedVariantInput ||
        !addToCartButton
    ) {
        return;
    }

    const numberFormatter = new Intl.NumberFormat("fa-IR")

    function formatNumber(value){
        return numberFormatter.format(value);
    }

    function resetVariant() {
        information.hidden = true;
        selectedVariantInput.value = "";
        addToCartButton.disabled = true;

        originalPriceContainer.hidden = true;
        discountContainer.hidden = true;

        originalPriceElement.textContent = "";
        discountElement.textContent = "";

        imageElement.hidden = true;
        imageElement.removeAttribute("src");
    }

    function displayVariant(variant) {
        information.hidden = false;

        skuElement.textContent = variant.sku;

        finalPriceElement.textContent = formatNumber(variant.final_price);

        originalPriceContainer.hidden = 
            Number(variant.discount_percent) <= 0;

        discountContainer.hidden = 
            Number(variant.discount_percent) <= 0;

        if (Number(variant.discount_percent) > 0) {
            originalPriceElement.textContent = formatNumber(
                variant.price
            );

            discountElement.textContent = formatNumber(
                variant.discount_percent
            );
        }

        stockElement.textContent = formatNumber(
            variant.available_stock
        );

        if (variant.image) {
            imageElement.src = variant.image;
            imageElement.hidden = false;
        } else {
            imageElement.hidden = true;
            imageElement.removeAttribute("src");
        }

        selectedVariantInput.value = variant.id;

        if (
            variant.is_in_stock && Number(variant.available_stock) > 0
        ) {
            addToCartButton.disabled = false;
            messageElement.textContent = "این تنوع موجود و قابل سفارش است.";
        } else {
            addToCartButton.disabled = true;
            messageElement.textContent = "این تنوع ثبت شده اما  در حال حاضر موجود نیست";
        }
    }

    function updateVariant() {
        resetVariant();

        const selectedAttributes = {};

        for (const selector of selectors) {
            const attributeId = selector.dataset.attributeId;
            const valueId = selector.value;

            if (!valueId) {
                messageElement.textContent = "لطفا همه ویژگی های محصول را انتخاب کنید";

                return;
            }

            selectedAttributes[attributeId] = Number(valueId);
        }

        const selectedAttributeCount = Object.keys(selectedAttributes).length;

        const matchingVariant = variants.find(function(variant) {
            const variantAttributes = variant.attributes;
            const variantAttributeIds = Object.keys(variantAttributes)

            if(variantAttributeIds.length !== selectedAttributeCount) {
                return false;
            }

            return Object.entries(selectedAttributes).every(
                function ([attributeId, valueId]) {
                    return (
                        Number(variantAttributes[attributeId]) === valueId
                    );
                }
            );
        });

        if (!matchingVariant) {
            messageElement.textContent = "برای این ترکیب تنوعی ثبت نشده است.";
            return;
        }

        displayVariant(matchingVariant)
    }

    selectors.forEach(function(selector) {
        selector.addEventListener("change", updateVariant)
    });

    const defaultVariant = variants.find(function (variant) {
        return (
            variant.is_in_stock && Number(variant.available_stock) > 0
        );
    }) || variants[0];

    if (!defaultVariant) {
        resetVariant();

        messageElement.textContent = "برای این محصول هنوز تنوع فعالی ثبت نشده است.";
        return;
    }

    for (const selector of selectors) {
        const attributeId = selector.dataset.attributeId;

        selector.value = defaultVariant.attributes[attributeId] ?? "";
    }

    updateVariant();
});