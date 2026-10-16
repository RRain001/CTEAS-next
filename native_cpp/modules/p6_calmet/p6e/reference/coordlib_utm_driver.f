      program p6e_coordlib_utm_driver
c --- Unmodified-source driver for the CALMET MICROI grid geometry.
c --- Reproduces calmet.for MICROI exactly:
c       call GLOBE1(cmapi,iutmi,tmsone,xlat1,xlat2,rnlat0,relon0,
c                   feast,fnorth,cmapo,idum,rdum,...,cactionll,vectill,vectoll)
c       xkm = xmap0 + (float(i)-0.5)*dgrid*0.001
c       ykm = ymap0 + (float(j)-0.5)*dgrid*0.001
c       call GLOBE(io6,cactionll,datum,vectill,datum,vectoll,
c                  xkm,ykm,xelon,xnlat,izone,c4hem)
c --- stdin: nx ny iutmzn / xmap0 ymap0 dgridkm / datum
c --- stdout: i j <xlat bits> <xlon bits>  (REAL*4 bit patterns)
      integer nx,ny,i,j,izone,iutmzn,idum,i8
      real xmap0,ymap0,dgridkm,dgrid
      real xkm,ykm,xelon,xnlat
      real rdum,tmsone,xlat1,xlat2,rnlat0,relon0,feast,fnorth
      real*8 vectill(9),vectoll(9)
      character*4 c4hem
      character*8 cmapi,cmapo,datum
      character*12 cactionll
c
      read(*,*) nx,ny,iutmzn
      read(*,*) xmap0,ymap0,dgridkm
      read(*,*) datum
c
      tmsone=1.00000
c --- MICROI: iutmi=iutmzn; UTMHEM='N' so the zone stays positive.
      iutmi=iutmzn
      cmapi='UTM'
      cmapo='LL'
      idum=0
      rdum=0.0
      xlat1=0.0
      xlat2=0.0
      rnlat0=0.0
      relon0=0.0
      feast=0.0
      fnorth=0.0
      call GLOBE1(cmapi,iutmi,tmsone,xlat1,xlat2,rnlat0,relon0,
     &            feast,fnorth,
     &            cmapo,idum,rdum,rdum,rdum,rdum,rdum,
     &            rdum,rdum,
     &            cactionll,vectill,vectoll)
c
      dgrid = 1000.*dgridkm
      do j=1,ny
        do i=1,nx
          xkm = xmap0 + (float(i)-0.5)*dgrid*0.001
          ykm = ymap0 + (float(j)-0.5)*dgrid*0.001
          call GLOBE(6,cactionll,datum,vectill,datum,vectoll,
     &               xkm,ykm,xelon,xnlat,izone,c4hem)
          i8 = transfer(xnlat,i8)
          write(*,'(2(I6,1X),Z8.8,1X)',advance='no') i,j,i8
          i8 = transfer(xelon,i8)
          write(*,'(Z8.8)') i8
        enddo
      enddo
      end
