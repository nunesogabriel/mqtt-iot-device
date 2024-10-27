import logging
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types

class SimpleSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.logger.setLevel(logging.DEBUG)  # Configurando nível de log para DEBUG

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """ Configuração inicial do switch ao conectar """
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.info("Switch conectado: %s", datapath.id)

        # Instalar a regra para enviar todos os pacotes para o controlador por padrão
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        """ Função auxiliar para adicionar regras de fluxo no switch """
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.logger.debug("Adicionando fluxo no switch %s com prioridade %s", datapath.id, priority)

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """ Lida com pacotes que chegam ao controlador """
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        # Evitar pacotes LLDP ou de broadcast IPv6
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            self.logger.debug("Pacote LLDP ignorado no switch %s", datapath.id)
            return
        if eth.ethertype == ether_types.ETH_TYPE_IPV6:
            self.logger.debug("Pacote IPv6 ignorado no switch %s", datapath.id)
            return

        dst = eth.dst
        src = eth.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("Pacote recebido no switch %s: origem=%s destino=%s porta=%s", dpid, src, dst, in_port)

        # Aprender o MAC da porta de entrada
        self.mac_to_port[dpid][src] = in_port

        # Se o MAC de destino for conhecido, enviar o pacote para a porta correta
        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
            self.logger.debug("Destino conhecido. Encaminhando o pacote para a porta %s", out_port)
        else:
            # Caso contrário, enviar o pacote para todas as portas (comportamento de hub)
            out_port = ofproto.OFPP_FLOOD
            self.logger.debug("Destino desconhecido. Flooding do pacote.")

        actions = [parser.OFPActionOutput(out_port)]

        # Instalar um fluxo para evitar que este pacote passe pelo controlador no futuro
        if out_port != ofproto.OFPP_FLOOD:
            self.logger.info("Instalando fluxo para %s -> %s no switch %s", src, dst, datapath.id)
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            self.add_flow(datapath, 1, match, actions)

        # Enviar o pacote para a saída apropriada
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)