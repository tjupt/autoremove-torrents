import ply.yacc as yacc
from . import logger
from .condition.avgdownloadspeed import AverageDownloadSpeedCondition
from .condition.avguploadspeed import AverageUploadSpeedCondition
from .condition.base import Comparer
from .condition.connectedleecher import ConnectedLeecherCondition
from .condition.connectedseeder import ConnectedSeederCondition
from .condition.createtime import CreateTimeCondition
from .condition.downloaded import DownloadsCondition
from .condition.downloadspeed import DownloadSpeedCondition
from .condition.lastactivity import LastActivityCondition
from .condition.leecher import LeecherCondition
from .condition.progress import ProgressCondition
from .condition.ratio import RatioCondition
from .condition.seeder import SeederCondition
from .condition.seedingtime import SeedingTimeCondition
from .condition.downloadingtime import DownloadingTimeCondition
from .condition.size import SizeCondition
from .condition.uploaded import UploadsCondition
from .condition.uploadratio import UploadRatioCondition
from .condition.uploadspeed import UploadSpeedCondition
from .conditionlexer import ConditionLexer
from .exception.nosuchcondition import NoSuchCondition
from .exception.syntaxerror import ConditionSyntaxError
from .client.hnr_api import HnrClient
from .condition.hnr import HnrCondition

class ConditionParser(object):
    # Condition Map (as constant)
    _condition_map = {
        'average_downloadspeed': AverageDownloadSpeedCondition,
        'average_uploadspeed': AverageUploadSpeedCondition,
        'connected_leecher': ConnectedLeecherCondition,
        'connected_seeder': ConnectedSeederCondition,
        'create_time': CreateTimeCondition,
        'download': DownloadsCondition,
        'download_speed': DownloadSpeedCondition,
        'last_activity': LastActivityCondition,
        'leecher': LeecherCondition,
        'progress': ProgressCondition,
        'ratio': RatioCondition,
        'seeder': SeederCondition,
        'seeding_time': SeedingTimeCondition,
        'downloading_time': DownloadingTimeCondition,
        'size': SizeCondition,
        'upload': UploadsCondition,
        'upload_ratio': UploadRatioCondition,
        'upload_speed': UploadSpeedCondition,
        'hnr': HnrCondition,
    }

    # Condition expression
    _expression = ''

    # All of the torrents
    _torrent_list = set()
    # To be removed torrents
    remove = set()
    # To be remained torrents
    remain = set()

    tokens = ConditionLexer.tokens

    precedence = (
        ('left', 'AND', 'OR'),
    )

    op = {
        ConditionLexer.t_LT: Comparer.LT,
        ConditionLexer.t_GT: Comparer.GT,
        ConditionLexer.t_EQ: Comparer.EQ,
    }

    def p_statement(self, t):
        'statement : expression'
        self.remove = t[1]
        self.remain = self._torrent_list.difference(self.remove)

    def p_sub_expression(self, t):
        'expression : LPAREN expression RPAREN'
        t[0] = t[2]

    def p_and_or_expression(self, t):
        '''
        expression : expression AND expression
                    | expression OR expression
        '''
        if t[2] == 'and': # Intersection
            t[0] = t[1].intersection(t[3])
        elif t[2] == 'or': # Union
            t[0] = t[1].union(t[3])

    def p_relation_op(self, t):
        '''
        relation_op : LT
                     | GT
                     | EQ
        '''
        t[0] = t[1]
    
    def p_relation_expression(self, t):
        '''
        expression : STRING relation_op NUMBER
                    | STRING relation_op STRING
        '''
        result = set()
        if t[1] in self._condition_map:
            obj = self._condition_map[t[1]](t[3], self.op[t[2]])
            obj.apply(self._client_status, self._torrent_list)
            result = obj.remove
        else:
            raise NoSuchCondition('The condition \'%s\' is not supported.' % t[1])
        t[0] = result

    def p_error(self, p):
        if p:
            raise ConditionSyntaxError('Syntax Error: Unexpected token \'%s\'.' % p.value)
        else:
            raise ConditionSyntaxError('Syntax Error: Unexpected EOF.')
        self.remain = self._torrent_list
    
    def __init__(self, expression):
        # Initialize lexer and parser
        self.lexer = ConditionLexer()
        self.parser = yacc.yacc(module=self, optimize=1)
        # Save expression
        self._expression = expression
        # Logger
        self._logger = logger.Logger.register(__name__)
    
    # Apply this strategy
    def apply(self, client_status, torrents):
        self._torrent_list = set(torrents)
        self._client_status = client_status
        
        # 如果是 hnr 条件
        if hasattr(self, '_hnr_condition'):
            self._logger.debug("应用HNR条件...")
            self._hnr_condition.apply(client_status, torrents)
            self.remain = self._hnr_condition.remain
            self.remove = self._hnr_condition.remove
            return
            
        # 其他条件的处理
        self.parser.parse(self._expression)
        
    def parse_condition(self, conf):
        """解析配置"""
        if 'hnr' in conf:
            self._logger.debug("发现HNR配置，初始化HNR条件")
            hnr_conf = conf['hnr']
            
            self._logger.debug(f"HNR API配置: host={hnr_conf['host']}")
            client = HnrClient(
                host=hnr_conf['host'],
                api_token=hnr_conf['api_token']
            )
            
            self._logger.debug(f"HNR配置: {hnr_conf}")
            
            self._hnr_condition = HnrCondition(
                client=client,
                config=hnr_conf
            )
            self._logger.debug("HNR条件初始化完成")
            return self._hnr_condition
            
        return None