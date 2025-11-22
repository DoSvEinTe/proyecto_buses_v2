from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponseRedirect
from .models import Bus, DocumentoVehiculo, Mantenimiento
from .forms import BusForm, MantenimientoForm, DocumentoVehiculoForm

# Vistas de Buses (Proyecto Principal)
class BusListView(ListView):
    model = Bus
    template_name = 'flota/bus_list.html'
    context_object_name = 'buses'
    paginate_by = 20

    def get_queryset(self):
        return Bus.objects.all().order_by('-creado_en')


class BusDetailView(DetailView):
    model = Bus
    template_name = 'flota/bus_detail.html'
    context_object_name = 'bus'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bus = self.object
        # Agregar mantenimientos y documentos al contexto
        context['mantenimientos'] = bus.mantenimientos.all().order_by('-fecha_mantenimiento')
        context['documentos'] = bus.documentos.all().order_by('-fecha_vencimiento')
        context['today'] = timezone.now().date()
        return context


class BusCreateView(CreateView):
    model = Bus
    form_class = BusForm
    template_name = 'flota/bus_form.html'
    success_url = reverse_lazy('flota:bus_list')

    def form_valid(self, form):
        messages.success(self.request, f'Bus {form.instance.placa} creado exitosamente.')
        return super().form_valid(form)


class BusUpdateView(UpdateView):
    model = Bus
    form_class = BusForm
    template_name = 'flota/bus_form.html'
    success_url = reverse_lazy('flota:bus_list')

    def form_valid(self, form):
        messages.success(self.request, f'Bus {form.instance.placa} actualizado exitosamente.')
        return super().form_valid(form)


class BusDeleteView(View):
    """
    Vista personalizada para eliminar buses con opción de reemplazo de viajes.
    Si el bus tiene viajes asociados, muestra una página para elegir un bus de reemplazo
    o dejar los viajes sin bus asignado.
    """
    def get(self, request, pk):
        bus = get_object_or_404(Bus, pk=pk)
        viajes = bus.viajes.all()
        
        # Si no hay viajes, eliminar directamente
        if not viajes.exists():
            bus.delete()
            messages.success(request, f'Bus {bus.placa} eliminado exitosamente.')
            return redirect('flota:bus_list')
        
        # Si hay viajes, mostrar página de reemplazo
        otros_buses = Bus.objects.exclude(pk=pk)
        context = {
            'bus': bus,
            'viajes': viajes,
            'otros_buses': otros_buses,
            'viajes_count': viajes.count()
        }
        return render(request, 'flota/bus_delete_replacement.html', context)
    
    def post(self, request, pk):
        bus = get_object_or_404(Bus, pk=pk)
        viajes = bus.viajes.all()
        
        action = request.POST.get('action')
        
        if action == 'replace':
            # Reemplazar bus por otro
            nuevo_bus_id = request.POST.get('nuevo_bus_id')
            if not nuevo_bus_id:
                messages.error(request, 'Debe seleccionar un bus de reemplazo.')
                return redirect('flota:bus_delete', pk=pk)
            
            nuevo_bus = get_object_or_404(Bus, pk=nuevo_bus_id)
            viajes.update(bus=nuevo_bus)
            bus.delete()
            messages.success(
                request,
                f'Bus {bus.placa} eliminado. Sus {viajes.count()} viaje(s) han sido asignados a {nuevo_bus.placa}.'
            )
        
        elif action == 'remove':
            # Dejar viajes sin bus (poner NULL si es permitido, o crear una lógica especial)
            # Nota: Como bus tiene PROTECT, modificamos el campo a null=True temporalmente o usamos otra estrategia
            # Por ahora, vamos a mantener los viajes pero sin bus (requiere cambiar modelo)
            messages.warning(
                request,
                f'Bus {bus.placa} eliminado. Sus {viajes.count()} viaje(s) quedan sin bus asignado.'
            )
            bus.delete()
        
        return redirect('flota:bus_list')


# Vistas de Mantenimientos (De Patentes)
class MantenimientoCreateView(CreateView):
    model = Mantenimiento
    form_class = MantenimientoForm
    template_name = 'flota/mantenimiento_form.html'
    
    def form_valid(self, form):
        bus = get_object_or_404(Bus, pk=self.kwargs['bus_id'])
        form.instance.bus = bus
        messages.success(self.request, 'Mantenimiento registrado correctamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('flota:bus_detail', kwargs={'pk': self.kwargs['bus_id']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bus'] = get_object_or_404(Bus, pk=self.kwargs['bus_id'])
        return context


class MantenimientoUpdateView(UpdateView):
    model = Mantenimiento
    form_class = MantenimientoForm
    template_name = 'flota/mantenimiento_form.html'
    
    def get_success_url(self):
        messages.success(self.request, 'Mantenimiento actualizado correctamente.')
        return reverse_lazy('flota:bus_detail', kwargs={'pk': self.object.bus.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bus'] = self.object.bus
        context['editing'] = True
        return context


class MantenimientoDeleteView(DeleteView):
    model = Mantenimiento
    template_name = 'flota/mantenimiento_confirm_delete.html'
    
    def get_success_url(self):
        messages.success(self.request, 'Mantenimiento eliminado correctamente.')
        return reverse_lazy('flota:bus_detail', kwargs={'pk': self.object.bus.pk})


# Vistas de Documentos (De Patentes)
class DocumentoVehiculoCreateView(CreateView):
    model = DocumentoVehiculo
    form_class = DocumentoVehiculoForm
    template_name = 'flota/documento_form.html'
    
    def form_valid(self, form):
        bus = get_object_or_404(Bus, pk=self.kwargs['bus_id'])
        form.instance.bus = bus
        messages.success(self.request, 'Documento registrado correctamente.')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('flota:bus_detail', kwargs={'pk': self.kwargs['bus_id']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bus'] = get_object_or_404(Bus, pk=self.kwargs['bus_id'])
        return context


class DocumentoVehiculoUpdateView(UpdateView):
    model = DocumentoVehiculo
    form_class = DocumentoVehiculoForm
    template_name = 'flota/documento_form.html'
    
    def get_success_url(self):
        messages.success(self.request, 'Documento actualizado correctamente.')
        return reverse_lazy('flota:bus_detail', kwargs={'pk': self.object.bus.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bus'] = self.object.bus
        context['editing'] = True
        return context


class DocumentoVehiculoDeleteView(DeleteView):
    model = DocumentoVehiculo
    template_name = 'flota/documento_confirm_delete.html'
    
    def get_success_url(self):
        messages.success(self.request, 'Documento eliminado correctamente.')
        return reverse_lazy('flota:bus_detail', kwargs={'pk': self.object.bus.pk})