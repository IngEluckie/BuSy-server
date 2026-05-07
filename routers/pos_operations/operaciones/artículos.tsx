import React, { useEffect, useState } from 'react'
import './style.css'
import { Modal } from '../../ventanaModal/modal'

type ActionButton = {
  id: string
  label: string
  shortcut: string
  icon: string
}

type ActionModalContent = {
  title: string
  description: string
}

type ResultColumn = {
  id: string
  label?: string
  icon?: string
  className?: string
}

type ProductTab = 'general' | 'inventario' | 'atributos'
type ProductType = 'simple'
type ProductTypeOption = 'Producto simple' | 'Producto compuesto' | 'Servicio'
type ProductModalMode = 'create' | 'edit'
type InventoryTrackingMode = 'tracked' | 'untracked'
type ReservationPolicy = 'disabled' | 'allowed'
type StockStatus = 'in_stock' | 'out_of_stock' | 'backorder'

type ProductAttribute = {
  id: string
  name: string
  values: string[]
  visible: boolean
}

type ProductImage = {
  id: string
  url: string
  altText?: string
  isPrimary: boolean
  order: number
}

type SimpleProduct = {
  id: string
  type: ProductType
  general: {
    name: string
    shortDescription: string
    longDescription: string
    regularPrice: number | null
    salePrice: number | null
  }
  inventory: {
    sku: string
    trackingMode: InventoryTrackingMode
    quantity: number | null
    reservationPolicy: ReservationPolicy | null
    lowStockThreshold: number | null
    stockStatus: StockStatus
  }
  attributes: ProductAttribute[]
  media: {
    images: ProductImage[]
  }
  metadata: {
    createdAt: string
    updatedAt: string
    isActive: boolean
  }
}

type SimpleProductValidationErrors = Partial<Record<'name' | 'shortDescription' | 'regularPrice' | 'sku', string>>

const topActions: ActionButton[] = [
  { id: 'agregar', label: 'Agregar', shortcut: '(F3)', icon: '➕' },
  { id: 'editar', label: 'Editar', shortcut: '(F4)', icon: '✏️' },
  { id: 'recargar', label: 'Recargar', shortcut: '(F5)', icon: '↻' },
  { id: 'eliminar', label: 'Eliminar', shortcut: '(F6)', icon: '✖' },
  { id: 'ajustar', label: 'Ajustar', shortcut: '(F8)', icon: '⚖' },
  { id: 'clonar', label: 'Clonar', shortcut: '(F9)', icon: '⧉' },
  { id: 'nubexis', label: 'NubExis', shortcut: '(Alt + E)', icon: '☁' },
  { id: 'imprimir', label: 'Imp.', shortcut: '(Ctrl + P)', icon: '▥' },
]

const actionModalContent: Record<ActionButton['id'], ActionModalContent> = {
  agregar: {
    title: 'Agregar artículo',
    description: 'Aquí podrás capturar la información de un nuevo artículo y registrarlo en el catálogo.'
  },
  editar: {
    title: 'Editar artículo',
    description: 'Aquí podrás modificar la información del artículo seleccionado.'
  },
  recargar: {
    title: 'Recargar artículos',
    description: 'Aquí podrás refrescar la información cargada en la interfaz de artículos.'
  },
  eliminar: {
    title: 'Eliminar artículo',
    description: 'Aquí podrás confirmar la baja del artículo seleccionado del catálogo.'
  },
  ajustar: {
    title: 'Ajustar existencias',
    description: 'Aquí podrás registrar ajustes de inventario para el artículo seleccionado.'
  },
  clonar: {
    title: 'Clonar artículo',
    description: 'Aquí podrás duplicar la configuración del artículo seleccionado para crear uno nuevo.'
  },
  nubexis: {
    title: 'Sincronizar con NubExis',
    description: 'Aquí podrás revisar y ejecutar acciones relacionadas con la integración de NubExis.'
  },
  imprimir: {
    title: 'Imprimir artículo',
    description: 'Aquí podrás preparar la impresión de etiquetas, fichas o reportes del artículo seleccionado.'
  }
}

const resultColumns: ResultColumn[] = [
  { id: 'clave', label: 'Clave/Descripción', className: 'articulos-ui__results-cell--description' },
  { id: 'existencias', label: 'Exist.', className: 'articulos-ui__results-cell--stock' },
  { id: 'precio', label: 'Precio', className: 'articulos-ui__results-cell--price' },
  { id: 'etiquetas', icon: '🏷', className: 'articulos-ui__results-cell--icon' },
  { id: 'config', icon: '⚙', className: 'articulos-ui__results-cell--icon' },
  { id: 'enlace', icon: '🔗', className: 'articulos-ui__results-cell--icon' },
  { id: 'cubo', icon: '🧊', className: 'articulos-ui__results-cell--icon' },
  { id: 'layout', icon: '▧', className: 'articulos-ui__results-cell--icon' },
]

const productTabs: Array<{ id: ProductTab; label: string }> = [
  { id: 'general', label: 'General' },
  { id: 'inventario', label: 'Inventario' },
  { id: 'atributos', label: 'Atributos' },
]

const productTypeOptions: ProductTypeOption[] = ['Producto simple', 'Producto compuesto', 'Servicio']
const PRODUCTS_PER_PAGE = 20

const createClientId = (prefix: string) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`

const createEmptyProductAttribute = (): ProductAttribute => ({
  id: createClientId('attr'),
  name: '',
  values: [],
  visible: true,
})

const createEmptySimpleProduct = (): SimpleProduct => {
  const now = new Date().toISOString()

  return {
    id: createClientId('prod'),
    type: 'simple',
    general: {
      name: '',
      shortDescription: '',
      longDescription: '',
      regularPrice: null,
      salePrice: null,
    },
    inventory: {
      sku: '',
      trackingMode: 'tracked',
      quantity: 1,
      reservationPolicy: 'disabled',
      lowStockThreshold: 1,
      stockStatus: 'in_stock',
    },
    attributes: [
      createEmptyProductAttribute(),
    ],
    media: {
      images: [],
    },
    metadata: {
      createdAt: now,
      updatedAt: now,
      isActive: true,
    },
  }
}

const createEditableSimpleProductDraft = (product: SimpleProduct): SimpleProduct => ({
  ...product,
  attributes: product.attributes.length > 0 ? product.attributes : [createEmptyProductAttribute()],
})

const parseNumberInput = (value: string) => {
  if (value.trim() === '') {
    return null
  }

  const parsedValue = Number(value)

  return Number.isNaN(parsedValue) ? null : parsedValue
}

export const Articulos = () => {
  const [openActionId, setOpenActionId] = useState<ActionButton['id'] | null>(null)
  const [activeProductTab, setActiveProductTab] = useState<ProductTab>('general')
  const [productType, setProductType] = useState<ProductTypeOption>(productTypeOptions[0])
  const [productModalMode, setProductModalMode] = useState<ProductModalMode>('create')
  const [simpleProductDraft, setSimpleProductDraft] = useState<SimpleProduct>(() => createEmptySimpleProduct())
  const [simpleProducts, setSimpleProducts] = useState<SimpleProduct[]>([])
  const [currentProductPage, setCurrentProductPage] = useState(1)
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null)
  const [adjustingProductId, setAdjustingProductId] = useState<string | null>(null)
  const [adjustmentQuantityDraft, setAdjustmentQuantityDraft] = useState('')
  const [adjustmentError, setAdjustmentError] = useState<string | null>(null)
  const [simpleProductErrors, setSimpleProductErrors] = useState<SimpleProductValidationErrors>({})
  const [productModalError, setProductModalError] = useState<string | null>(null)

  const trackInventory = simpleProductDraft.inventory.trackingMode === 'tracked'
  const primaryAttribute = simpleProductDraft.attributes[0]
  const isProductModalOpen = openActionId === 'agregar' || openActionId === 'editar'
  const totalProductPages = Math.ceil(simpleProducts.length / PRODUCTS_PER_PAGE)
  const currentProductPageLabel = totalProductPages === 0 ? 0 : currentProductPage
  const pageStartIndex = (currentProductPage - 1) * PRODUCTS_PER_PAGE
  const paginatedProducts = simpleProducts.slice(pageStartIndex, pageStartIndex + PRODUCTS_PER_PAGE)
  const canGoToPreviousProductPage = totalProductPages > 0 && currentProductPage > 1
  const canGoToNextProductPage = totalProductPages > 0 && currentProductPage < totalProductPages

  useEffect(() => {
    if (totalProductPages === 0) {
      if (currentProductPage !== 1) {
        setCurrentProductPage(1)
      }

      return
    }

    if (currentProductPage > totalProductPages) {
      setCurrentProductPage(totalProductPages)
    }
  }, [currentProductPage, totalProductPages])

  useEffect(() => {
    const handleEscapeSelection = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !openActionId && !productModalError) {
        if (adjustingProductId) {
          event.preventDefault()
          setAdjustingProductId(null)
          setAdjustmentQuantityDraft('')
          setAdjustmentError(null)

          return
        }

        setSelectedProductId(null)
      }
    }

    window.addEventListener('keydown', handleEscapeSelection)

    return () => {
      window.removeEventListener('keydown', handleEscapeSelection)
    }
  }, [adjustingProductId, openActionId, productModalError])

  const clearAdjustment = () => {
    setAdjustingProductId(null)
    setAdjustmentQuantityDraft('')
    setAdjustmentError(null)
  }

  const startProductAdjustment = (product: SimpleProduct) => {
    setSelectedProductId(product.id)
    setAdjustingProductId(product.id)
    setAdjustmentQuantityDraft(String(product.inventory.quantity ?? 0))
    setAdjustmentError(null)
  }

  const parseAdjustmentQuantity = () => {
    if (!/^\d+$/.test(adjustmentQuantityDraft.trim())) {
      return null
    }

    return Number(adjustmentQuantityDraft)
  }

  const confirmProductAdjustment = () => {
    const nextQuantity = parseAdjustmentQuantity()

    if (nextQuantity === null) {
      setAdjustmentError('Ingresa un entero mayor o igual a 0.')

      return
    }

    setSimpleProducts((currentProducts) => (
      currentProducts.map((product) => (
        product.id === adjustingProductId
          ? {
              ...product,
              inventory: {
                ...product.inventory,
                quantity: nextQuantity,
              },
              metadata: {
                ...product.metadata,
                updatedAt: new Date().toISOString(),
              },
            }
          : product
      ))
    ))
    clearAdjustment()
  }

  const decrementAdjustmentQuantity = () => {
    const nextQuantity = Math.max(0, parseAdjustmentQuantity() ?? 0)

    setAdjustmentQuantityDraft(String(Math.max(0, nextQuantity - 1)))
    setAdjustmentError(null)
  }

  const incrementAdjustmentQuantity = () => {
    const nextQuantity = parseAdjustmentQuantity() ?? 0

    setAdjustmentQuantityDraft(String(nextQuantity + 1))
    setAdjustmentError(null)
  }

  const handleOpenActionModal = (actionId: ActionButton['id']) => {
    if (actionId === 'agregar') {
      clearAdjustment()
      setProductModalMode('create')
      setSimpleProductDraft(createEmptySimpleProduct())
      setSimpleProductErrors({})
      setActiveProductTab('general')
      setOpenActionId(actionId)

      return
    }

    if (actionId === 'editar') {
      const selectedProduct = simpleProducts.find((product) => product.id === selectedProductId)

      if (!selectedProduct) {
        setProductModalError('No se ha seleccionado producto')

        return
      }

      clearAdjustment()
      setProductModalMode('edit')
      setSimpleProductDraft(createEditableSimpleProductDraft(selectedProduct))
      setSimpleProductErrors({})
      setActiveProductTab('general')
      setOpenActionId(actionId)

      return
    }

    if (actionId === 'eliminar') {
      const selectedProduct = simpleProducts.find((product) => product.id === selectedProductId)

      if (!selectedProduct) {
        setProductModalError('No artículo seleccionado')

        return
      }

      clearAdjustment()
      setSimpleProducts((currentProducts) => (
        currentProducts.filter((product) => product.id !== selectedProduct.id)
      ))
      setCurrentProductPage((currentPage) => {
        const nextTotalPages = Math.ceil((simpleProducts.length - 1) / PRODUCTS_PER_PAGE)

        return Math.max(1, Math.min(currentPage, nextTotalPages || 1))
      })
      setSelectedProductId(null)

      return
    }

    if (actionId === 'ajustar') {
      const selectedProduct = simpleProducts.find((product) => product.id === selectedProductId)

      if (!selectedProduct) {
        setProductModalError('No artículo seleccionado')

        return
      }

      if (selectedProduct.inventory.trackingMode !== 'tracked') {
        setProductModalError('El producto no maneja cantidad de inventario.')

        return
      }

      startProductAdjustment(selectedProduct)

      return
    }

    if (actionId === 'clonar') {
      const selectedProduct = simpleProducts.find((product) => product.id === selectedProductId)

      if (!selectedProduct) {
        setProductModalError('No artículo seleccionado')

        return
      }

      clearAdjustment()
      const now = new Date().toISOString()
      const clonedProduct: SimpleProduct = {
        ...selectedProduct,
        id: createClientId('prod'),
        general: {
          ...selectedProduct.general,
          name: `${selectedProduct.general.name} (clon)`,
        },
        attributes: selectedProduct.attributes.map((attribute) => ({
          ...attribute,
          id: createClientId('attr'),
        })),
        media: {
          images: selectedProduct.media.images.map((image) => ({
            ...image,
            id: createClientId('img'),
          })),
        },
        metadata: {
          ...selectedProduct.metadata,
          createdAt: now,
          updatedAt: now,
        },
      }

      setSimpleProducts((currentProducts) => [...currentProducts, clonedProduct])
      setCurrentProductPage(Math.ceil((simpleProducts.length + 1) / PRODUCTS_PER_PAGE))
      setSelectedProductId(clonedProduct.id)

      return
    }

    setOpenActionId(actionId)
  }

  const handleCloseActionModal = () => {
    setOpenActionId(null)
  }

  const handleCloseProductModalError = () => {
    setProductModalError(null)
  }

  const handleSelectProduct = (productId: string) => {
    if (adjustingProductId && adjustingProductId !== productId) {
      clearAdjustment()
    }

    setSelectedProductId(productId)
  }

  const handleEditProduct = (product: SimpleProduct) => {
    if (adjustingProductId === product.id) {
      return
    }

    clearAdjustment()
    setSelectedProductId(product.id)
    setProductModalMode('edit')
    setSimpleProductDraft(createEditableSimpleProductDraft(product))
    setSimpleProductErrors({})
    setActiveProductTab('general')
    setOpenActionId('editar')
  }

  const handlePreviousProductPage = () => {
    clearAdjustment()
    setCurrentProductPage((currentPage) => Math.max(1, currentPage - 1))
  }

  const handleNextProductPage = () => {
    clearAdjustment()
    setCurrentProductPage((currentPage) => Math.min(totalProductPages || 1, currentPage + 1))
  }

  const clearSimpleProductErrors = (fields: Array<keyof SimpleProductValidationErrors>) => {
    setSimpleProductErrors((currentErrors) => {
      const nextErrors = { ...currentErrors }

      fields.forEach((field) => {
        delete nextErrors[field]
      })

      return nextErrors
    })
  }

  const updateSimpleProductGeneral = (general: Partial<SimpleProduct['general']>) => {
    const fieldsToClear: Array<keyof SimpleProductValidationErrors> = []

    if ('name' in general) {
      fieldsToClear.push('name')
    }

    if ('shortDescription' in general) {
      fieldsToClear.push('shortDescription')
    }

    if ('regularPrice' in general) {
      fieldsToClear.push('regularPrice')
    }

    if (fieldsToClear.length > 0) {
      clearSimpleProductErrors(fieldsToClear)
    }

    setSimpleProductDraft((currentProduct) => ({
      ...currentProduct,
      general: {
        ...currentProduct.general,
        ...general,
      },
      metadata: {
        ...currentProduct.metadata,
        updatedAt: new Date().toISOString(),
      },
    }))
  }

  const updateSimpleProductInventory = (inventory: Partial<SimpleProduct['inventory']>) => {
    if ('sku' in inventory) {
      clearSimpleProductErrors(['sku'])
    }

    setSimpleProductDraft((currentProduct) => ({
      ...currentProduct,
      inventory: {
        ...currentProduct.inventory,
        ...inventory,
      },
      metadata: {
        ...currentProduct.metadata,
        updatedAt: new Date().toISOString(),
      },
    }))
  }

  const updatePrimaryAttribute = (attribute: Partial<ProductAttribute>) => {
    setSimpleProductDraft((currentProduct) => ({
      ...currentProduct,
      attributes: currentProduct.attributes.map((currentAttribute, index) => (
        index === 0
          ? {
              ...currentAttribute,
              ...attribute,
            }
          : currentAttribute
      )),
      metadata: {
        ...currentProduct.metadata,
        updatedAt: new Date().toISOString(),
      },
    }))
  }

  const handleTrackInventoryChange = (isTracked: boolean) => {
    updateSimpleProductInventory({
      trackingMode: isTracked ? 'tracked' : 'untracked',
      quantity: isTracked ? simpleProductDraft.inventory.quantity ?? 1 : null,
      reservationPolicy: isTracked ? simpleProductDraft.inventory.reservationPolicy ?? 'disabled' : null,
      lowStockThreshold: isTracked ? simpleProductDraft.inventory.lowStockThreshold : null,
      stockStatus: isTracked ? 'in_stock' : simpleProductDraft.inventory.stockStatus,
    })
  }

  const buildSimpleProductToSave = (): SimpleProduct => {
    const now = new Date().toISOString()

    return {
      ...simpleProductDraft,
      general: {
        ...simpleProductDraft.general,
        name: simpleProductDraft.general.name.trim(),
        shortDescription: simpleProductDraft.general.shortDescription.trim(),
        longDescription: simpleProductDraft.general.longDescription.trim(),
      },
      inventory: {
        ...simpleProductDraft.inventory,
        sku: simpleProductDraft.inventory.sku.trim(),
      },
      attributes: simpleProductDraft.attributes
        .map((attribute) => ({
          ...attribute,
          name: attribute.name.trim(),
          values: attribute.values.map((value) => value.trim()).filter(Boolean),
        }))
        .filter((attribute) => attribute.name || attribute.values.length > 0),
      metadata: {
        ...simpleProductDraft.metadata,
        updatedAt: now,
      },
    }
  }

  const validateSimpleProductGeneral = (product: SimpleProduct) => {
    const validationErrors: SimpleProductValidationErrors = {}

    if (!product.general.name) {
      validationErrors.name = 'El nombre del producto es obligatorio.'
    }

    if (!product.general.shortDescription) {
      validationErrors.shortDescription = 'La descripción corta es obligatoria.'
    }

    if (product.general.regularPrice === null) {
      validationErrors.regularPrice = 'El precio regular es obligatorio.'
    }

    return validationErrors
  }

  const validateSimpleProductInventory = (product: SimpleProduct) => {
    const validationErrors: SimpleProductValidationErrors = {}

    if (!product.inventory.sku) {
      validationErrors.sku = 'El SKU es obligatorio.'
    }

    return validationErrors
  }

  const handleProductModalPrimaryAction = () => {
    const productToSave = buildSimpleProductToSave()

    if (activeProductTab === 'general') {
      const validationErrors = validateSimpleProductGeneral(productToSave)

      if (Object.keys(validationErrors).length > 0) {
        setSimpleProductErrors(validationErrors)

        return
      }

      clearSimpleProductErrors(['name', 'shortDescription', 'regularPrice'])
      setActiveProductTab('inventario')

      return
    }

    if (activeProductTab === 'inventario') {
      const validationErrors = validateSimpleProductInventory(productToSave)

      if (Object.keys(validationErrors).length > 0) {
        setSimpleProductErrors(validationErrors)

        return
      }

      clearSimpleProductErrors(['sku'])
      setActiveProductTab('atributos')

      return
    }

    const validationErrors = {
      ...validateSimpleProductGeneral(productToSave),
      ...validateSimpleProductInventory(productToSave),
    }

    if (Object.keys(validationErrors).length > 0) {
      setSimpleProductErrors(validationErrors)
      setActiveProductTab(validationErrors.name || validationErrors.shortDescription || validationErrors.regularPrice ? 'general' : 'inventario')

      return
    }

    if (productModalMode === 'edit') {
      setSimpleProducts((currentProducts) => (
        currentProducts.map((product) => (
          product.id === productToSave.id ? productToSave : product
        ))
      ))
      setSelectedProductId(productToSave.id)
    } else {
      setSimpleProducts((currentProducts) => [...currentProducts, productToSave])
      setCurrentProductPage(Math.ceil((simpleProducts.length + 1) / PRODUCTS_PER_PAGE))
      setSelectedProductId(productToSave.id)
    }

    setSimpleProductDraft(createEmptySimpleProduct())
    setSimpleProductErrors({})
    setActiveProductTab('general')
    setProductModalMode('create')
    clearAdjustment()
    handleCloseActionModal()
  }

  const productPrimaryActionLabel = activeProductTab === 'atributos' ? 'Guardar' : 'Siguiente'
  const productModalTitle = `Datos del producto - ${productModalMode === 'edit' ? 'Editar' : 'Agregar'}`

  return (
    <section className='articulos-ui'>
      <header className='articulos-ui__topbar'>
        {topActions.map((action) => (
          <button
            key={action.id}
            className='articulos-ui__top-action'
            onClick={() => handleOpenActionModal(action.id)}
            type='button'
          >
            <span className='articulos-ui__top-icon' aria-hidden='true'>
              {action.icon}
            </span>
            <span className='articulos-ui__top-text'>
              {action.label} {action.shortcut}
            </span>
          </button>
        ))}
      </header>

      <div className='articulos-ui__main-wrap'>
        <div className='articulos-ui__main'>
          <section className='articulos-ui__left-column'>
            <div className='articulos-ui__search-row'>
              <button type='button' className='articulos-ui__search-filter' aria-label='Filtrar búsqueda'>
                🔻
              </button>
              <input
                className='articulos-ui__search-input'
                type='text'
                placeholder='Ingresa código de barras, folio o nombre del artículo que quieres consultar.'
              />
              <button type='button' className='articulos-ui__search-button' aria-label='Buscar artículo'>
                🔎
              </button>
            </div>

            <div className='articulos-ui__results'>
              <div className='articulos-ui__results-head' role='row'>
                {resultColumns.map((column) => (
                  <div key={column.id} className={`articulos-ui__results-cell ${column.className ?? ''}`} role='columnheader'>
                    {column.label ?? (
                      <span aria-hidden='true' className='articulos-ui__head-icon'>
                        {column.icon}
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <div className='articulos-ui__results-body' role='rowgroup'>
                {simpleProducts.length === 0 ? (
                  <p className='articulos-ui__results-empty'>Sin coincidencias para mostrar.</p>
                ) : (
                  paginatedProducts.map((product) => (
                    <div
                      aria-selected={selectedProductId === product.id}
                      className={`articulos-ui__results-row ${selectedProductId === product.id ? 'articulos-ui__results-row--selected' : ''}`}
                      key={product.id}
                      onClick={() => handleSelectProduct(product.id)}
                      onDoubleClick={() => handleEditProduct(product)}
                      role='row'
                    >
                      <div className='articulos-ui__results-data articulos-ui__results-cell--description' role='cell'>
                        <strong>{product.inventory.sku || product.id}</strong>
                        <span>{product.general.name || 'Producto sin nombre'}</span>
                      </div>
                      <div className='articulos-ui__results-data articulos-ui__results-cell--stock' role='cell'>
                        {adjustingProductId === product.id ? (
                          <div
                            className='articulos-ui__stock-adjuster'
                            onClick={(event) => event.stopPropagation()}
                            onDoubleClick={(event) => event.stopPropagation()}
                          >
                            <button
                              aria-label='Disminuir existencias'
                              className='articulos-ui__stock-adjuster-button'
                              onClick={decrementAdjustmentQuantity}
                              type='button'
                            >
                              -
                            </button>
                            <input
                              aria-invalid={Boolean(adjustmentError)}
                              aria-label='Nueva cantidad de existencias'
                              className='articulos-ui__stock-adjuster-input'
                              inputMode='numeric'
                              onChange={(event) => {
                                setAdjustmentQuantityDraft(event.target.value)
                                setAdjustmentError(null)
                              }}
                              onKeyDown={(event) => {
                                if (event.key === 'Enter') {
                                  event.preventDefault()
                                  confirmProductAdjustment()
                                }

                                if (event.key === 'Escape') {
                                  event.preventDefault()
                                  clearAdjustment()
                                }
                              }}
                              type='text'
                              value={adjustmentQuantityDraft}
                            />
                            <button
                              aria-label='Aumentar existencias'
                              className='articulos-ui__stock-adjuster-button'
                              onClick={incrementAdjustmentQuantity}
                              type='button'
                            >
                              +
                            </button>
                          </div>
                        ) : (
                          product.inventory.quantity ?? '-'
                        )}
                      </div>
                      <div className='articulos-ui__results-data articulos-ui__results-cell--price' role='cell'>
                        {product.general.regularPrice !== null ? `$${product.general.regularPrice.toFixed(2)}` : '-'}
                      </div>
                      <div className='articulos-ui__results-data articulos-ui__results-cell--icon' role='cell'>-</div>
                      <div className='articulos-ui__results-data articulos-ui__results-cell--icon' role='cell'>-</div>
                      <div className='articulos-ui__results-data articulos-ui__results-cell--icon' role='cell'>-</div>
                      <div className='articulos-ui__results-data articulos-ui__results-cell--icon' role='cell'>-</div>
                      <div className='articulos-ui__results-data articulos-ui__results-cell--icon' role='cell'>-</div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <footer className='articulos-ui__pagination'>
              <button
                aria-label='Página anterior'
                className='articulos-ui__page-arrow'
                disabled={!canGoToPreviousProductPage}
                onClick={handlePreviousProductPage}
                type='button'
              >
                ◀
              </button>

              <div className='articulos-ui__page-meta'>
                <span className='articulos-ui__page-label'>Página</span>
                <input className='articulos-ui__page-input' type='text' value={currentProductPageLabel} readOnly />
                <span className='articulos-ui__page-separator'>de</span>
                <input className='articulos-ui__page-input' type='text' value={totalProductPages} readOnly />
              </div>

              <button
                aria-label='Página siguiente'
                className='articulos-ui__page-arrow'
                disabled={!canGoToNextProductPage}
                onClick={handleNextProductPage}
                type='button'
              >
                ▶
              </button>
            </footer>
          </section>

          <aside className='articulos-ui__right-column'>
            <h2 className='articulos-ui__detail-title'>Artículo Seleccionado</h2>

            <div className='articulos-ui__preview'>
              <button type='button' className='articulos-ui__preview-arrow' aria-label='Imagen anterior'>
                ❮
              </button>
              <div className='articulos-ui__preview-placeholder' aria-label='Imagen del artículo'>
                📷
              </div>
              <button type='button' className='articulos-ui__preview-arrow' aria-label='Imagen siguiente'>
                ❯
              </button>
            </div>

            <div className='articulos-ui__detail-empty'>
              <span>-</span>
              <span>-</span>
            </div>
          </aside>
        </div>
      </div>

      {topActions.map((action) => {
        const modalContent = actionModalContent[action.id]

        if (action.id === 'agregar') {
          return (
            <Modal
              key={action.id}
              isOpen={isProductModalOpen}
              onClose={handleCloseActionModal}
              width='calc(100vw - 40px)'
              maxWidth='calc(100vw - 40px)'
              height='calc(100vh - 40px)'
              showCloseButton={false}
              className='articulos-ui__product-modal-shell'
              bodyClassName='articulos-ui__product-modal-body'
            >
              <div className='articulos-ui__product-modal'>
                <header className='articulos-ui__product-modal-header'>
                  <div className='articulos-ui__product-modal-title-row'>
                    <h2 className='articulos-ui__product-modal-title'>{productModalTitle}</h2>
                    <label className='articulos-ui__product-type-label'>
                      <span className='articulos-ui__product-type-text'>Tipo de producto</span>
                      <select
                        className='articulos-ui__product-type-select'
                        value={productType}
                        onChange={(event) => setProductType(event.target.value as ProductTypeOption)}
                      >
                        {productTypeOptions.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>

                  <button
                    aria-label='Cerrar ventana modal'
                    className='articulos-ui__product-modal-close'
                    onClick={handleCloseActionModal}
                    type='button'
                  >
                    ×
                  </button>
                </header>

                <div className='articulos-ui__product-modal-layout'>
                  <section className='articulos-ui__product-form-panel'>
                    <nav className='articulos-ui__product-tabs' aria-label='Secciones del producto'>
                      {productTabs.map((tab) => (
                        <button
                          key={tab.id}
                          className={`articulos-ui__product-tab ${activeProductTab === tab.id ? 'articulos-ui__product-tab--active' : ''}`}
                          onClick={() => setActiveProductTab(tab.id)}
                          type='button'
                        >
                          {tab.label}
                        </button>
                      ))}
                    </nav>

                    <div className='articulos-ui__product-tab-panel'>
                      {activeProductTab === 'general' ? (
                        <div className='articulos-ui__product-general-grid'>
                          <label className='articulos-ui__product-field articulos-ui__product-field--name'>
                            <span className='articulos-ui__product-label'>Nombre del producto:</span>
                            <input
                              aria-invalid={Boolean(simpleProductErrors.name)}
                              className='articulos-ui__product-input'
                              onChange={(event) => updateSimpleProductGeneral({ name: event.target.value })}
                              required
                              type='text'
                              value={simpleProductDraft.general.name}
                            />
                            {simpleProductErrors.name && (
                              <span className='articulos-ui__product-error'>{simpleProductErrors.name}</span>
                            )}
                          </label>

                          <label className='articulos-ui__product-field articulos-ui__product-field--short'>
                            <span className='articulos-ui__product-label'>Descripción corta:</span>
                            <input
                              aria-invalid={Boolean(simpleProductErrors.shortDescription)}
                              className='articulos-ui__product-input'
                              onChange={(event) => updateSimpleProductGeneral({ shortDescription: event.target.value })}
                              required
                              type='text'
                              value={simpleProductDraft.general.shortDescription}
                            />
                            {simpleProductErrors.shortDescription && (
                              <span className='articulos-ui__product-error'>{simpleProductErrors.shortDescription}</span>
                            )}
                          </label>

                          <label className='articulos-ui__product-field articulos-ui__product-field--large'>
                            <span className='articulos-ui__product-label'>Descripción amplia:</span>
                            <textarea
                              className='articulos-ui__product-textarea'
                              onChange={(event) => updateSimpleProductGeneral({ longDescription: event.target.value })}
                              value={simpleProductDraft.general.longDescription}
                            />
                          </label>

                          <div className='articulos-ui__product-price-grid'>
                            <label className='articulos-ui__product-price-field'>
                              <span className='articulos-ui__product-label'>Precio regular:</span>
                              <input
                                aria-invalid={Boolean(simpleProductErrors.regularPrice)}
                                className='articulos-ui__product-input articulos-ui__product-input--price'
                                inputMode='decimal'
                                onChange={(event) => updateSimpleProductGeneral({ regularPrice: parseNumberInput(event.target.value) })}
                                required
                                type='text'
                                value={simpleProductDraft.general.regularPrice ?? ''}
                              />
                              {simpleProductErrors.regularPrice && (
                                <span className='articulos-ui__product-error'>{simpleProductErrors.regularPrice}</span>
                              )}
                            </label>

                            <label className='articulos-ui__product-price-field'>
                              <span className='articulos-ui__product-label'>Precio rebajado:</span>
                              <input
                                className='articulos-ui__product-input articulos-ui__product-input--price'
                                inputMode='decimal'
                                onChange={(event) => updateSimpleProductGeneral({ salePrice: parseNumberInput(event.target.value) })}
                                type='text'
                                value={simpleProductDraft.general.salePrice ?? ''}
                              />
                            </label>
                          </div>
                        </div>
                      ) : activeProductTab === 'inventario' ? (
                        <div className='articulos-ui__inventory-form'>
                          <label className='articulos-ui__inventory-field'>
                            <span className='articulos-ui__inventory-label articulos-ui__inventory-label--link'>SKU</span>
                            <input
                              aria-invalid={Boolean(simpleProductErrors.sku)}
                              className='articulos-ui__inventory-input'
                              onChange={(event) => updateSimpleProductInventory({ sku: event.target.value })}
                              required
                              type='text'
                              value={simpleProductDraft.inventory.sku}
                            />
                            <button className='articulos-ui__inventory-help' type='button' aria-label='Ayuda sobre SKU'>
                              ?
                            </button>
                            {simpleProductErrors.sku && (
                              <span className='articulos-ui__inventory-error'>{simpleProductErrors.sku}</span>
                            )}
                          </label>

                          <div className='articulos-ui__inventory-field articulos-ui__inventory-field--check'>
                            <span className='articulos-ui__inventory-label'>Gestión de inventario</span>
                            <label className='articulos-ui__inventory-check-label'>
                              <input
                                checked={trackInventory}
                                className='articulos-ui__inventory-checkbox'
                                onChange={(event) => handleTrackInventoryChange(event.target.checked)}
                                type='checkbox'
                              />
                              <span>Hacer seguimiento de la cantidad de inventario de este producto</span>
                            </label>
                          </div>

                          {trackInventory ? (
                            <>
                              <label className='articulos-ui__inventory-field'>
                                <span className='articulos-ui__inventory-label'>Cantidad</span>
                                <input
                                  className='articulos-ui__inventory-input'
                                  min='0'
                                  onChange={(event) => updateSimpleProductInventory({ quantity: parseNumberInput(event.target.value) })}
                                  type='number'
                                  value={simpleProductDraft.inventory.quantity ?? ''}
                                />
                                <button className='articulos-ui__inventory-help' type='button' aria-label='Ayuda sobre cantidad'>
                                  ?
                                </button>
                              </label>

                              <fieldset className='articulos-ui__inventory-field articulos-ui__inventory-reservations'>
                                <legend className='articulos-ui__inventory-label'>¿Permitir reservas?</legend>
                                <div className='articulos-ui__inventory-radio-stack'>
                                  <label className='articulos-ui__inventory-radio-label'>
                                    <input
                                      checked={simpleProductDraft.inventory.reservationPolicy === 'disabled'}
                                      name='inventory-reservations'
                                      onChange={() => updateSimpleProductInventory({ reservationPolicy: 'disabled' })}
                                      type='radio'
                                    />
                                    <span>No permitir</span>
                                  </label>
                                  <label className='articulos-ui__inventory-radio-label'>
                                    <input
                                      checked={simpleProductDraft.inventory.reservationPolicy === 'allowed'}
                                      name='inventory-reservations'
                                      onChange={() => updateSimpleProductInventory({ reservationPolicy: 'allowed' })}
                                      type='radio'
                                    />
                                    <span>Permitir</span>
                                  </label>
                                </div>
                              </fieldset>

                              <label className='articulos-ui__inventory-field'>
                                <span className='articulos-ui__inventory-label'>Umbral de pocos productos (1)</span>
                                <input
                                  className='articulos-ui__inventory-input'
                                  onChange={(event) => updateSimpleProductInventory({ lowStockThreshold: parseNumberInput(event.target.value) })}
                                  type='text'
                                  value={simpleProductDraft.inventory.lowStockThreshold ?? ''}
                                />
                                <button className='articulos-ui__inventory-help' type='button' aria-label='Ayuda sobre umbral de pocas existencias'>
                                  ?
                                </button>
                              </label>
                            </>
                          ) : (
                            <fieldset className='articulos-ui__inventory-field articulos-ui__inventory-reservations'>
                              <legend className='articulos-ui__inventory-label'>Estado de inventario</legend>
                              <div className='articulos-ui__inventory-radio-stack'>
                                <label className='articulos-ui__inventory-radio-label'>
                                  <input
                                    checked={simpleProductDraft.inventory.stockStatus === 'in_stock'}
                                    name='inventory-status'
                                    onChange={() => updateSimpleProductInventory({ stockStatus: 'in_stock' })}
                                    type='radio'
                                  />
                                  <span>Hay existencias</span>
                                </label>
                                <label className='articulos-ui__inventory-radio-label'>
                                  <input
                                    checked={simpleProductDraft.inventory.stockStatus === 'out_of_stock'}
                                    name='inventory-status'
                                    onChange={() => updateSimpleProductInventory({ stockStatus: 'out_of_stock' })}
                                    type='radio'
                                  />
                                  <span>Sin existencias</span>
                                </label>
                                <label className='articulos-ui__inventory-radio-label'>
                                  <input
                                    checked={simpleProductDraft.inventory.stockStatus === 'backorder'}
                                    name='inventory-status'
                                    onChange={() => updateSimpleProductInventory({ stockStatus: 'backorder' })}
                                    type='radio'
                                  />
                                  <span>Se puede reservar</span>
                                </label>
                              </div>
                              <button className='articulos-ui__inventory-help' type='button' aria-label='Ayuda sobre estado de inventario'>
                                ?
                              </button>
                            </fieldset>
                          )}
                        </div>
                      ) : (
                        <div className='articulos-ui__attributes-form'>
                          <header className='articulos-ui__attributes-toolbar'>
                            <div className='articulos-ui__attributes-actions'>
                              <button className='articulos-ui__attributes-button articulos-ui__attributes-button--primary' type='button'>
                                Añadir nuevo
                              </button>
                              <button className='articulos-ui__attributes-select' type='button'>
                                <span>Añadir existente</span>
                                <span aria-hidden='true'>⌄</span>
                              </button>
                            </div>
                            <button className='articulos-ui__attributes-link' type='button'>
                              Ampliar / Cerrar
                            </button>
                          </header>

                          <section className='articulos-ui__attribute-card'>
                            <header className='articulos-ui__attribute-card-head'>
                              <h3>Atributo nuevo</h3>
                              <div className='articulos-ui__attribute-card-actions'>
                                <button className='articulos-ui__attribute-delete' type='button'>
                                  Eliminar
                                </button>
                                <button className='articulos-ui__attribute-icon-button' type='button' aria-label='Reordenar atributo'>
                                  ≡
                                </button>
                                <button className='articulos-ui__attribute-icon-button' type='button' aria-label='Contraer atributo'>
                                  ▴
                                </button>
                              </div>
                            </header>

                            <div className='articulos-ui__attribute-fields'>
                              <div className='articulos-ui__attribute-left'>
                                <label className='articulos-ui__attribute-field'>
                                  <span>Nombre:</span>
                                  <input
                                    className='articulos-ui__attribute-input'
                                    onChange={(event) => updatePrimaryAttribute({ name: event.target.value })}
                                    type='text'
                                    placeholder='por ejemplo, la longitud o el peso'
                                    value={primaryAttribute.name}
                                  />
                                </label>

                                <label className='articulos-ui__attribute-visible'>
                                  <input
                                    checked={primaryAttribute.visible}
                                    onChange={(event) => updatePrimaryAttribute({ visible: event.target.checked })}
                                    type='checkbox'
                                  />
                                  <span>Visible en la página de productos</span>
                                </label>
                              </div>

                              <label className='articulos-ui__attribute-field articulos-ui__attribute-field--values'>
                                <span>Valor(es):</span>
                                <textarea
                                  className='articulos-ui__attribute-textarea'
                                  onChange={(event) => updatePrimaryAttribute({
                                    values: event.target.value.split('|').map((value) => value.trim()),
                                  })}
                                  placeholder='Introduce un texto descriptivo. Utiliza «|» para separar los distintos valores.'
                                  value={primaryAttribute.values.join(' | ')}
                                />
                              </label>
                            </div>

                            <footer className='articulos-ui__attribute-footer'>
                              <button className='articulos-ui__attribute-save' type='button' disabled>
                                Guardar atributos
                              </button>
                              <button className='articulos-ui__attributes-link' type='button'>
                                Ampliar / Cerrar
                              </button>
                            </footer>
                          </section>
                        </div>
                      )}
                    </div>
                  </section>

                  <aside className='articulos-ui__product-image-panel'>
                    <button className='articulos-ui__product-image-button' type='button'>
                      Agregar imagen
                    </button>

                    <div className='articulos-ui__product-image-preview' aria-label='Vista previa de imagen del producto'>
                      <span aria-hidden='true'>▥</span>
                    </div>

                    <div className='articulos-ui__product-thumbs'>
                      <button className='articulos-ui__product-thumbs-arrow' type='button' aria-label='Imagen anterior'>
                        ‹
                      </button>
                      <div className='articulos-ui__product-thumb articulos-ui__product-thumb--active' />
                      <div className='articulos-ui__product-thumb' />
                      <div className='articulos-ui__product-thumb' />
                      <div className='articulos-ui__product-thumb' />
                      <button className='articulos-ui__product-thumbs-arrow' type='button' aria-label='Imagen siguiente'>
                        ›
                      </button>
                    </div>

                    <button className='articulos-ui__product-save' onClick={handleProductModalPrimaryAction} type='button'>
                      {productPrimaryActionLabel}
                    </button>
                  </aside>
                </div>
              </div>
            </Modal>
          )
        }

        if (action.id === 'editar') {
          return null
        }

        return (
          <Modal
            key={action.id}
            isOpen={openActionId === action.id}
            onClose={handleCloseActionModal}
            title={modalContent.title}
            width='min(92vw, 520px)'
          >
            <div className='articulos-ui__action-modal'>
              <div className='articulos-ui__action-modal-icon' aria-hidden='true'>
                {action.icon}
              </div>
              <div className='articulos-ui__action-modal-copy'>
                <p className='articulos-ui__action-modal-text'>{modalContent.description}</p>
                <p className='articulos-ui__action-modal-shortcut'>
                  Acceso rápido: <strong>{action.shortcut}</strong>
                </p>
              </div>

              <div className='articulos-ui__action-modal-actions'>
                <button
                  className='articulos-ui__action-modal-button articulos-ui__action-modal-button--primary'
                  onClick={handleCloseActionModal}
                  type='button'
                >
                  Continuar
                </button>
                <button
                  className='articulos-ui__action-modal-button'
                  onClick={handleCloseActionModal}
                  type='button'
                >
                  Cerrar
                </button>
              </div>
            </div>
          </Modal>
        )
      })}

      <Modal
        isOpen={Boolean(productModalError)}
        onClose={handleCloseProductModalError}
        title='Editar artículo'
        width='min(92vw, 420px)'
      >
        <div className='articulos-ui__action-modal'>
          <p className='articulos-ui__action-modal-text'>{productModalError}</p>

          <div className='articulos-ui__action-modal-actions'>
            <button
              className='articulos-ui__action-modal-button articulos-ui__action-modal-button--primary'
              onClick={handleCloseProductModalError}
              type='button'
            >
              Cerrar
            </button>
          </div>
        </div>
      </Modal>
    </section>
  )
}
